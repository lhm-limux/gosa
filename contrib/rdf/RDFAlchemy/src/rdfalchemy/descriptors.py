#!/usr/bin/env python
# encoding: utf-8
"""
descriptors.py

Created by Philip Cooper on 2008-02-03.
Copyright (c) 2008 Openvest. All rights reserved.
"""

from rdflib import URIRef, BNode, Namespace
from rdflib.Identifier import Identifier 
from rdfalchemy import rdfSubject, Literal 
from copy import copy

import logging

__all__=["rdfSingle","rdfMultiple","rdfList","rdfContainer","owlTransitive"]

#console = logging.StreamHandler()
#formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
#console.setFormatter(formatter)
log=logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)
#log.addHandler(console)

RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#") # need the RDF['_%d'%i] ability

# helper function, might be somewhere in rdflib I need to look for it there
def getList(sub, pred=None, db=None):
    """Attempts to return a list from sub (subject that is)
    passed in if it is a Collection or a Container (Bag,Seq or Alt)"""
    if not db:
        if isinstance(sub,rdfSubject):
            db=sub.db
        else:
            db=rdfSubject.db
    if isinstance(sub,rdfSubject):
        sub = sub.resUri
    if pred:
        base = db.value(sub, pred, any=True)
    else:
        # if there was no predicate assume a base node was passed in
        base=sub
    if type(base) != BNode:
        # Doesn't look like a list or a collection, just return multiple values (or an error?)
        val=[o for o in db.objects(sub, pred)]
        return val
    members=[]
    first = db.value(base, RDF.first)
    # OK let's work at returning a list if there is an RDF.first
    if first:
        while first:
            members.append(first)
            base = db.value(base, RDF.rest)
            first = db.value(base, RDF.first)
        return members
    # OK let's work at returning a Collection (Seq,Bag or Alt) if was no RDF.first
    else:
        i=1        
        first=db.value(base, RDF._1)
        if not first:
            raise AttributeError, "Not a list, or collection but another type of BNode"
        while first:
            members.append(first)
            i += 1
            first=db.value(base, RDF['_%d'%i])
        return members
        
def value2object(value):
    """suitable for a triple takes a value and returns a Literal, URIRef or BNode 
    suitable for a triple"""
    if isinstance(value, rdfSubject):
        return value.resUri
    elif isinstance(value, Identifier):
        return value
    else:
        return Literal(value)


##################################################################################
# define a series of descriptors
# each one will map an attribute of a class (derived from rdfObjet) to a predicate 
##################################################################################


class rdfAbstract(object):
    """Abstract base class for descriptors
    Descriptors are to map class instance variables to predicates
    optional cacheName is where to store items
    range_type is the rdf:type of the range of this predicate"""
    def __init__(self, pred, cacheName=None, range_type=None):
        self.pred = pred
        self.name = cacheName or pred
        self.range_type = range_type
    
    @property
    def range_class(self):
        """return the class that this descriptor is mapped to through the range_type"""
        if self.range_type:
            try:
                return self._mappedClass
            except AttributeError:
                log.warn("Descriptor %s has range of: %s but not yet mapped"%(self, self.range_type))
                return rdfSubject
        else:
            return rdfSubject
            
    def __delete__(self, obj):
        """deletes or removes from the database triples with:
          obj.resUri as subject and self.pred as predicate
          if the object of that triple is a Literal that stop
          if the object of that triple is a BNode 
          then cascade the delete if that BNode has no further references to it
          i.e. it is not the object in any other triples.
        """ 
        # be done ala getList above
        log.debug("DELETE with descriptor for %s on %s"%(self.pred, obj.n3()))        
        # first drop the cached value
        if obj.__dict__.has_key(self.name):
            del obj.__dict__[self.name]
        # next, drop the triples
        obj.__delitem__(self.pred)         



                    
class rdfSingle(rdfAbstract):
    '''This is a Descriptor
    Takes a the URI of the predicate at initialization
    Expects to return a single item
    on Assignment will set that value to the 
    ONLY triple with that subject,predicate pair'''
    def __init__(self, pred, cacheName=None, range_type=None):
        super(rdfSingle, self).__init__(pred, cacheName, range_type)
        
    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Geting with descriptor %s for %s"%(self.pred,obj.n3()))
        val=obj.__getitem__(self.pred)        
        if isinstance(val, (rdfSubject, BNode, URIRef)):
            val = self.range_class(val)
        obj.__dict__[self.name]= val
        return val
    
    def __set__(self, obj, value):
        log.debug("SET with descriptor value %s of type %s"%(value,type(value)))
        #setattr(obj, self.name, value)  #this recurses indefinatly
        if isinstance(value,(list,tuple,set)):
            raise AttributeError("to set an rdfSingle you must pass in a single value")
        obj.__dict__[self.name]= value
        o =value2object(value)
        obj.db.set((obj.resUri, self.pred, o))
        
   
class rdfMultiple(rdfAbstract):
    '''This is a Descriptor    
       Expects to return a list of values (could be a list of one)'''
    def __init__(self, pred, cacheName=None, range_type=None):
        super(rdfMultiple, self).__init__(pred, cacheName, range_type)
        
    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        val=[o for o in obj.db.objects(obj.resUri, self.pred)]
        log.debug("Geting with descriptor %s for %s"%(self.pred,obj.n3()))
        # check to see if this is a Container or Collection
        # if so, return collection as a list
        if len(val) == 1 \
           and (obj.db.value(o,RDF.first) or obj.db.value(o,RDF._1)): 
                  val=getList(obj, self.pred)
        val=[(isinstance(v, (BNode,URIRef)) and self.range_class(v) or v.toPython()) for v in val]
        obj.__dict__[self.name]= val
        return val

    def __set__(self, obj, newvals):
        log.debug("SET with descriptor value %s of type %s"%(newvals,type(newvals)))
        if not isinstance(newvals, (list,tuple)):
            raise AttributeError("to set a rdfMultiple you must pass in a list (it can be a list of one)")
        try:
            oldvals = obj.__dict__[self.name]
        except KeyError:
            oldvals = []
            obj.__dict__[self.name] = oldvals
        for value in oldvals:
            if value not in newvals:
                obj.db.remove((obj.resUri,self.pred, value2object(value)))
                log.debug("removing: %s, %s, %s"%(obj.n3(),self.pred,value))
        for value in newvals:
            if value not in oldvals:
                obj.db.add((obj.resUri, self.pred, value2object(value)))
                log.debug("adding: %s, %s, %s"%(obj.n3(),self.pred,value))
        obj.__dict__[self.name] = copy(newvals)
        
class rdfBest(rdfSingle):
    '''This is a Descriptor  that returns one value that is the 
    "best" result out of possible multiple matches
    
    returns a single value or None
    
    It is the responsibility of the select_fun to return a default
    like choices[0] if no "Best" is found'''
    
    def __init__(self, pred, select_fun = None, cacheName=None, range_type=None ):
        if select_fun:
            self.select_fun = select_fun
        super(rdfMultiple, self).__init__(pred, range_type)
        
    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Geting with descriptor %s for %s"%(self.pred,obj.n3()))
        vals=[o for o in obj.db.objects(obj.resUri, self.pred)]
        if vals:
            val = self.select_fun(vals)
            val = isinstance(val, (BNode,URIRef)) and self.range_class(val) or val.toPython()
        else:
            val = None
        obj.__dict__[self.name]= val
        return val

class rdfLocale(rdfBest):
    '''This is like rdfBest with a predefined select_fun to select 
    from multiple choices like labels or comments and select the one
    with the correct locale'''    
    def __init__(self, pred, lang, cacheName=None):
        self.lang = lang
        cacheNameLang = cacheName or ("%s@%s" % (pred, lang))
        super(rdfBest, self).__init__(pred,cacheName = cacheNameLang)

    def select_fun(self, choices):
        for x in choices:
            if isinstance(x,Literal) and x.language==self.lang:
                return x
        return choices[0]

class rdfList(rdfMultiple):
    '''This is a Descriptor    
       Expects to return a list of values (could be a list of one)
       `__set__` will set the predicate as a RDF List'''
       
    def __init__(self, pred, cacheName=None, range_type=None):
        super(rdfMultiple, self).__init__(pred, cacheName, range_type)
        
    def __get__(self, obj, cls):
        if obj is None:
            return self 
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]       
        #log.debug("Geting %s for %s"%(obj.db.qname(self.pred),obj.db.qname(obj.resUri)))
        log.debug("Geting %s for %s"%(self.pred,obj.n3()))
        base = obj.db.value(obj.resUri,self.pred)
        if not base or base==RDF.nil:
            return []
        members=[]
        first = obj.db.value(base, RDF.first)
        # OK let's work at returning a list if there is an RDF.first
        if not first:
            raise AttributeError, ("expected node [%s] to be a list but it's not" %base.n3())
        while first:
            members.append(first)
            base = obj.db.value(base, RDF.rest)
            first = obj.db.value(base, RDF.first)

        val=[((isinstance(v,BNode) or isinstance(v,URIRef)) and self.range_class(v) or v.toPython()) for v in members]
        obj.__dict__[self.name] = val
        return val
        
    def __set__(self, obj, newvals):
        log.debug("SET with descriptor value %s of type %s"%(newvals,type(newvals)))
        if not isinstance(newvals, (list,tuple)):
            raise AttributeError("to set a rdfList you must pass in a list (it can be a list of one)")
        try:
            oldvals = obj.__dict__[self.name]
        except KeyError:
            oldvals = []
            obj.__dict__[self.name] = oldvals
        oldhead = obj.db.value(obj.resUri,self.pred)
##          # This is a stack style where retrevial is oppisite of how it starts out
##         newnode = RDF.nil
##         for value in newvals:
##             almostnewnode = newnode
##             newnode = BNode()            
##             obj.db.add((newnode, RDF.first, value2object(value)))
##             obj.db.add((newnode, RDF.rest, almostnewnode))        
        if not newvals:
            newhead = RDF.nil
        else:
            newhead = BNode()
            newtail = newhead
            oldtail = None
            for value in newvals:
                if oldtail:
                    obj.db.add((oldtail, RDF.rest, newtail))
                obj.db.add((newtail, RDF.first, value2object(value)))
                oldtail = newtail
                newtail = BNode()
            obj.db.add((oldtail, RDF.rest, RDF.nil))
        obj.db.set((obj.resUri, self.pred, newhead))
        if oldhead:
            rdfSubject(oldhead)._remove(db=obj.db)
        obj.__dict__[self.name] = copy(newvals)


        
class rdfContainer(rdfMultiple):
    '''This is a Descriptor    
       Expects to return a list of values (could be a list of one)
       
       container_type in `__init__` should be one of 

               * rdf:Seq
               * rdf:Bag
               * rdf:Alt
               
       `__set__` will set the predicate as a RDF Container type (defaults to rdf:Seq)'''

    def __init__(self, pred,  range_type=None, container_type="http://www.w3.org/1999/02/22-rdf-syntax-ns#Seq"):
        super(rdfMultiple, self).__init__(pred,  range_type=range_type)
        self.container_type = container_type
        
        
    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]               
        #log.debug("Geting %s for %s"%(obj.db.qname(self.pred),obj.db.qname(obj.resUri)))
        log.debug("Geting %s for %s"%(self.pred,obj.n3()))
        base = obj.db.value(obj.resUri, self.pred)
        if not base:
            return []
        members=[]
        i=1        
        first=obj.db.value(base, RDF._1)
        if not first:
            raise AttributeError, ("expected node [%s] to be a list but it's not" % base.n3())
        while first:
            members.append(first)
            i += 1
            first=obj.db.value(base, RDF['_%d'%i])

        val=[(isinstance(v,(BNode,URIRef)) and self.range_class(v) or v.toPython()) for v in members]
        obj.__dict__[self.name] = val
        return val
        
    def __set__(self, obj, newvals):
        log.debug("SET with descriptor value %s of type %s"%(newvals,type(newvals)))
        if not isinstance(newvals, (list,tuple)):
            raise AttributeError("to set a rdfList you must pass in a list (it can be a list of one)")
        seq = obj.db.value(obj.resUri, self.pred)
        if not seq:
            seq = BNode()
            obj.db.add((obj.resUri, self.pred, seq))
            obj.db.add((seq, RDF.type, RDF.Seq))
        for s,p,o in obj.db.triples((seq, None, None)):
            if p.startswith(RDF['_']):
                obj.db.remove((s,p,o))
                if isinstance(o, BNode) and o not in newvals:
                    rdfSubject(o)._remove(db=obj.db)
        for i in range(len(newvals)):
            obj.db.add((seq, RDF['_%i'%(i+1)], value2object(newvals[i])))
        obj.__dict__[self.name] = copy(newvals)
        
#################################################################################
# More owl-ish and rdfs-ish descriptors

class owlTransitive(rdfMultiple):
    """owlTransitive is a descriptor based on a transitive predicate
    The predicate should be of type owl:TransitiveProperty
    """
        
    def __get__(self, obj, cls):
        if obj is None:
            return self
        if self.name in obj.__dict__:
            return obj.__dict__[self.name]
        log.debug("Geting with descriptor %s for %s"%(self.pred,obj.n3()))
        val=[self.range_class(o) for o in obj.db.transitive_objects(obj.resUri, self.pred)]
        obj.__dict__[self.name]= val
        return val
