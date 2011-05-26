#!/usr/bin/env python
# encoding: utf-8
"""
rdfsSubject.py

rdfsSubject is similar to rdfsSubject but includes more
processing and *magic* based on an `RDF Schema`__

__ ::http://www.w3.org/TR/rdf-schema/

Created by Philip Cooper on 2008-05-14.
Copyright (c) 2008 Openvest. All rights reserved.
"""

from rdfalchemy import  rdfSubject, RDF, RDFS, Namespace, BNode, URIRef
from rdflib.Identifier import Identifier
from descriptors import *
from orm import mapper, allsub

import logging

log=logging.getLogger(__name__)
#log.debug("logger is %s",log.name)
log.setLevel(logging.INFO)


from weakref import WeakValueDictionary
import re

OWL = Namespace("http://www.w3.org/2002/07/owl#")

_all_ = ['rdfsSubject','rdfsClass','rdfsProperty',
         'owlObjectProperty','owlDatatypeProperty',
         'owlSymetricProperty', 'owlTransitiveProperty',
         'owlFunctionalProperty','owlInverseFunctionalProperty']


re_ns_n = re.compile(r'(.*[/#])(.*)')


class rdfsSubject(rdfSubject, Identifier):
    _weakrefs = WeakValueDictionary()
    
    def __new__(cls, resUri = None, schemaGraph=None, *args, **kwargs):
        if not resUri or isinstance(resUri, BNode) or issubclass(cls, BNode):  # create a bnode
            obj = BNode.__new__(cls, resUri)
            obj._nodetype = BNode
        elif isinstance(resUri, URIRef) or issubclass(cls, URIRef): # user the identifier passed in
            obj = URIRef.__new__(cls,resUri)
            obj._nodetype = URIRef            
        elif isinstance(resUri, rdfSubject):      # use the resUri of the subject passed in 
            obj= type(resUri.resUri).__new__(cls, resUri.resUri)
            obj._nodetype = type(resUri.resUri)
        elif isinstance(resUri, (str, unicode)):  # create one from a <uri> or _:bnode string
            if resUri[0]=="<" and resUri[-1]==">":
                obj=URIRef.__new__(cls, resUri[1:-1])
                obj._nodetype = URIRef                            
            elif resUri.startswith("_:"):
                obj=BNode.__new__(cls, resUri[2:])
                obj._nodetype = BNode                                            
        else:
            raise AttributeError("cannot construct rdfSubject from %s"%(str(resUri)))
        
        # At this point we have an obj to return...but we might want to look deeper
        # if there is an RDF:type entry on the Graph, find the mapped subclass and return
        # an object of that new type
        if resUri:
            rdf_type = obj[RDF.type]
            if rdf_type:
                class_dict = dict([(str(cl.rdf_type), cl) for cl in allsub(cls) if cl.rdf_type])
                subclass = class_dict.get(str(rdf_type.resUri),cls)
            else:
                subclass = cls
        else:
            subclass = cls
        
        # improve this do do some kind of hash with classname??
        # this uses _weakrefs to allow us to return an existing object
        # rather than copies 
        md5id = obj.md5_term_hash()
        newobj = rdfsSubject._weakrefs.get(md5id,None)
        log.debug("looking for weakref %s found %s",md5id,newobj)
        if newobj:
            return newobj
        newobj = super(rdfSubject,obj).__new__(subclass, obj.resUri)#, **kwargs)
        log.debug("add a weakref %s", newobj)
        newobj._nodetype = obj._nodetype
        rdfsSubject._weakrefs[newobj.md5_term_hash()] = newobj
        return newobj

    def __init__(self, resUri = None, **kwargs):
        if not self[RDF.type] and self.rdf_type:
            self.db.add((self.resUri,RDF.type,self.rdf_type))
        if kwargs:
            self._set_with_dict(kwargs)
            
            
    @property
    def resUri(self):
        return self._nodetype(unicode(self))
    
    def _splitname(self):
        return re.match(r'(.*[/#])(.*)',self.resUri).groups()
    
    @classmethod
    def ClassInstances(cls):
        """return a generator for instances of this rdf:type
        you can look in MyClass.rdf_type to see the predicate being used"""
        # Start with all things of "my" type in the db
        beenthere = set([])
        for i in cls.db.subjects(RDF.type, cls.rdf_type):
            if not i in beenthere:
                yield cls(i)
                beenthere.add(i)
        
        # for all subclasses of me in python do the same (recursivly)
        pySubClasses = allsub(cls)
        for sub in pySubClasses:
            for i in sub.ClassInstances():
                if not i in beenthere:
                    yield i 
                    beenthere.add(i)
                    
        # not done yet, for all db subclasses that I have not processed already...get them too
        dbSubClasses = rdfsClass(cls.rdf_type).transitive_subClasses
        moreSubClasses = [dbsub.resUri for dbsub in dbSubClasses 
                                if dbsub.resUri not in [pysub.rdf_type for pysub in pySubClasses]]
        for sub in moreSubClasses:
            for i in cls.db.subjects(RDF.type, sub):
                if '' and not i in beenthere:
                    yield i
                    beenthere.add(i)        
        
        

class rdfsClass(rdfsSubject):
    """rdfSbject with some RDF Schema addons
    *Some* inferencing is implied
    Bleading edge: be careful"""
    rdf_type = RDFS.Class
    comment = rdfSingle(RDFS.comment)
    label = rdfSingle(RDFS.label)    
    subClassOf = rdfMultiple(RDFS.subClassOf, range_type = RDFS.Class)
    
    @property
    def transitive_subClassOf(self):
        return [rdfsClass(s) for s in self.db.transitive_objects(self.resUri,RDFS.subClassOf)]

    @property
    def transitive_subClasses(self):
        return [rdfsClass(s) for s in self.db.transitive_subjects(RDFS.subClassOf, self.resUri)]

    @property
    def properties(self):
        # this doesn't get the rdfsProperty subclasses
        # return list(rdfsProperty.filter_by(domain=self.resUri))
        # TODO: why iterate all rdfsProperty subclasses
        #       try self.db.subjects(RDFS.domain,self.resUri)
        return [x for x in rdfsProperty.ClassInstances() if x.domain == self]
        
        
    
    def _emit_rdfSubject(self, visitedNS={}, visitedClass=set([])):
        """Procude the text that might be used for a .py file 
        TODO: This code should probably move into the commands module since that's the only place it's used"""
        ns,loc = self._splitname()
        try:
            prefix, qloc = self.db.qname(self.resUri).split(':')
        except:
            raise Exception("don't know how to handle a qname like %s" % self.db.qname(self.resUri))
        prefix = prefix.upper()
        
        if not visitedNS:
            src = """
from rdfalchemy import rdfSubject, Namespace, URIRef
from rdfalchemy.rdfsSubject import rdfsSubject
from rdfalchemy.orm import mapper

"""
            for k,v in self.db.namespaces():
                visitedNS[str(v)] = k.upper()
                src += '%s = Namespace("%s")\n' % (k.upper().replace('-','_'),v)
        else:
            src = ""
        
        mySupers = []
        for mySuper in self.subClassOf:
            sns, sloc = mySuper._splitname()
            if ns == sns:
                src += mySuper._emit_rdfSubject(visitedNS=visitedNS)
                mySupers.append( sloc.replace('-','_') )
                
                
                
        mySupers = ",".join(mySupers) or "rdfsSubject"
        src += '\nclass %s(%s):\n'%(loc.replace('-','_'), mySupers)
        src += '\t"""%s %s"""\n'%(self.label, self.comment)
        src += '\trdf_type = %s["%s"]\n' % (visitedNS[ns],loc)
            
            
        for p in self.properties:
            pns, ploc = p._splitname()
            ppy = '%s["%s"]' % (visitedNS[pns],ploc)
            try:
                assert  str(p.range[RDF.type].resUri).endswith('Class') # rdfs.Class and owl.Class
                rns, rloc = rdfsSubject(p.range)._splitname()
                range_type = ', range_type = %s["%s"]' % (visitedNS[rns],rloc)
            except Exception, e:
                range_type = ''
            src += '\t%s = rdfMultiple(%s%s)\n' % (ploc.replace('-','_') ,ppy,range_type)
            
        # Just want this once at the end
        src.replace("mapper()\n","")        
        src += "mapper()\n"
                   
        return src
    
class rdfsProperty(rdfsSubject):
    rdf_type = RDF.Property
    domain = rdfSingle(RDFS.domain, range_type=RDFS.Class)
    range = rdfSingle(RDFS.range)
    subPropertyOf = rdfMultiple(RDFS.subPropertyOf)
    default_descriptor = rdfMultiple  #

#####################################################################
# Beginings of a OWL package

class owlClass(rdfsClass):
    """rdfSbject with some RDF Schema addons
    *Some* inferencing is implied
    Bleading edge: be careful"""
    rdf_type = OWL["Class"]
    disjointWith = rdfMultiple(OWL["disjointWith"], range_type = OWL["Class"])
    equivalentClass = rdfMultiple(OWL["equivalentClass"], range_type = OWL["Class"])
    intersectionOf = rdfMultiple(OWL["intersectionOf"])
    unionOf = rdfMultiple(OWL["unionOf"])
    complementOf = rdfMultiple(OWL["complementOf"], range_type = OWL["Class"])


########################################
# properties        

class owlFunctionalProperty(rdfsProperty):
    rdf_type = OWL.FunctionalProperty
    default_descriptor = rdfSingle

class owlDatatypeProperty(rdfsProperty):
    rdf_type = OWL.DatatypeProperty
    range = rdfSingle(RDFS.range, range_type = RDFS.Class)
    default_descriptor = rdfMultiple
        
########################################
# Object properties        
class owlObjectProperty(rdfsProperty):
    rdf_type = OWL.ObjectProperty
    range = rdfSingle(RDFS.range, range_type = RDFS.Class)
    inverseOf = rdfSingle(OWL.inverseOf, range_type = OWL.ObjectProperty)
    default_descriptor = rdfMultiple

class owlInverseFunctionalProperty(owlObjectProperty):
    rdf_type = OWL.InverseFunctionalProperty
    default_descriptor = rdfSingle
                
class owlSymetricProperty(owlObjectProperty):
    rdf_type = OWL.SymetricProperty
    default_descriptor = rdfMultiple
        
class owlTransitiveProperty(owlObjectProperty):
    rdf_type = OWL.TransitiveProperty
    default_descriptor = owlTransitive
    
# this maps the return type of subClassOf back to rdfsClass
mapper()       

