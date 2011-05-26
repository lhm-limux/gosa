#!/usr/bin/env python
"""
rdfalchemy.py - a Simple API for RDF


Requires rdflib <http://www.rdflib.net/> version 2.3 ??.

"""

from rdflib import ConjunctiveGraph
from rdflib import BNode, Namespace, URIRef, RDF
from rdflib.Identifier import Identifier 
from rdfalchemy.exceptions import RDFAlchemyError
from rdfalchemy.Literal import Literal
import re

try:
    from hashlib import md5
except ImportError:
    from md5 import md5    

import logging
#console = logging.StreamHandler()
#formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
#console.setFormatter(formatter)

log=logging.getLogger(__name__)
#log.setLevel(logging.DEBUG)
#log.addHandler(console)

re_ns_n = re.compile('(.*[/#])(.*)')
    
# Note: Non data descriptors (get only) lookup in obj.__dict__ first
#       Data descriptors (get and set) use the __get__ first

##################################################################################
# define our Base Class for all "subjects" in python 
##################################################################################

class rdfSubject(object):
    db=ConjunctiveGraph()
    """Default graph for access to instances of this type"""
    rdf_type=None
    """rdf:type of instances of this class"""

    def __init__(self, resUri = None, **kwargs):
        """The constructor tries hard to do return you an rdfSubject

        :param resUri: the "resource uri". If `None` then create an instance with a BNode resUri.
        Can be given as one of:

           * an instance of an rdfSubject
           * an instance of a BNode or a URIRef
           * an n3 uriref string like: "<urn:isbn:1234567890>"
           * an n3 bnode string like: "_:xyz1234" 
        
        :param kwargs: is a set of values that will be set using the keys to find the appropriate descriptor"""
        
        if not resUri:  # create a bnode
            self.resUri = BNode()
            if self.rdf_type:
                self.db.add((self.resUri,RDF.type,self.rdf_type))
        elif isinstance(resUri, (BNode, URIRef)): # user the identifier passed in
            self.resUri=resUri
            if self.rdf_type and not list(self.db.triples((self.resUri,RDF.type,self.rdf_type))):
                self.db.add((self.resUri,RDF.type,self.rdf_type))
        elif isinstance(resUri, rdfSubject):      # use the resUri of the subject passed in 
            self.resUri=resUri.resUri 
            self.db=resUri.db
        elif isinstance(resUri, (str, unicode)):  # create one from a <uri> or _:bnode string
            if resUri[0]=="<" and resUri[-1]==">":
                self.resUri=URIRef(resUri[1:-1])
            elif resUri.startswith("_:"):
                self.resUri=BNode(resUri[2:])
        else:
            raise AttributeError("cannot construct rdfSubject from %s"%(str(resUri)))
        
        if kwargs:
            self._set_with_dict(kwargs)

                
    def n3(self):
        """n3 repr of this node"""
        return self.resUri.n3()
        

    @classmethod
    def _getdescriptor(cls, key):
        """__get_descriptor returns the descriptor for the key.
        It essentially cls.__dict__[key] with recursive calls to super"""
        # NOT SURE if mro is the way to do this or if we should call super or bases?
        for kls in cls.mro():
            if key in kls.__dict__:
                return kls.__dict__[key]
        raise AttributeError("descriptor %s not found for class %s" % (key,cls))
        
    #short term hack.  Need to go to a sqlalchemy 0.4 style query method
    # obj.query.get_by should map to obj.get_by  ..same for fetch_by
    @classmethod
    def query(cls):
        return cls    
    

    @classmethod
    def get_by(cls, **kwargs):
        """Class Method, returns a single instance of the class
        by a single kwarg.  the keyword must be a descriptor of the
        class.
        example:
        
            bigBlue = Company.get_by(symbol='IBM')

        :Note:
            the keyword should map to an rdf predicate
            that is of type owl:InverseFunctional"""
        if len(kwargs) != 1:
            raise ValueError("get_by wanted exactly 1 but got  %i args\nMaybe you wanted filter_by"%(len(kwargs)))
        key,value = kwargs.items()[0]
        if isinstance(value, (URIRef,BNode,Literal)):
            o = value
        else:
            o = Literal(value)
        pred=cls._getdescriptor(key).pred
        uri=cls.db.value(None,pred,o)
        if uri:
            return cls(uri)
        else:
            raise LookupError("%s = %s not found"%(key,value))

    @classmethod
    def filter_by(cls, **kwargs):
        """Class method returns a generator over classs instances
        meeting the kwargs conditions.

        Each keyword must be a class descriptor

        filter by RDF.type == cls.rdf_type is implicit

        Order helps, the first keyword should be the most restrictive
        """
        filters = []
        for key,value in kwargs.items():
            pred = cls._getdescriptor(key).pred
            # try to make the value be OK for the triple query as an object
            if isinstance(value, Identifier):
                obj = value
            else:
                obj = Literal(value)
            filters.append((pred,obj))
        # make sure we filter by type
        if not (RDF.type,cls.rdf_type) in filters:
            filters.append((RDF.type,cls.rdf_type))
        pred, obj = filters[0]
        log.debug("Checking %s, %s" % (pred,obj))
        for sub in cls.db.subjects(pred,obj):
            log.debug( "maybe %s" % sub )
            for pred,obj in filters[1:]:
                log.debug("Checking %s, %s" % (pred,obj))
                try:
                    cls.db.triples((sub,pred,obj)).next()
                except:
                    log.warn( "No %s" % sub )
                    break
            else:
                yield cls(sub)
        
    @classmethod
    def ClassInstances(cls):
        """return a generator for instances of this rdf:type
        you can look in MyClass.rdf_type to see the predicate being used"""
        beenthere = set([])
        for i in cls.db.subjects(RDF.type, cls.rdf_type):
            if not i in beenthere:
                yield cls(i)
                beenthere.add(i)

    @classmethod
    def GetRandom(cls):
        """for develoment just returns a random instance of this class"""
        from random import choice
        xii=list(cls.ClassInstances())
        return choice(xii)
        
    def __hash__(self):
        return hash("ranD0Mi$h_"+self.n3())
    
    def __cmp__(self, other):
        return cmp(self.n3(), other.n3())
    
    def __repr__(self):
        return """%s('%s')""" % (self.__class__.__name__, self.n3())
    
    def __str__(self):
        return str(self.resUri)
    
    def __getitem__(self, pred):
        log.debug("Getting with __getitem__ %s for %s"%(pred,self.n3()))
        val=self.db.value(self.resUri, pred)
        if isinstance(val,Literal):
            val =  val.toPython() 
        elif isinstance(val, (BNode,URIRef)): 
            val=rdfSubject(val) 
        return val
        
        
    def __delitem__(self, pred):
        log.debug("Deleting with __delitem__ %s for %s"%(pred,self))
        for s,p,o in self.db.triples((self.resUri, pred, None)):
            self.db.remove((s,p,o))
            #finally if the object in the triple was a bnode 
            #cascade delete the thing it referenced
            # ?? FIXME Do we really want to cascade if it's an rdfSubject??
            if isinstance(o, (BNode, rdfSubject)):
                rdfSubject(o)._remove(db=self.db,cascade='bnode')
        
    def _set_with_dict(self, kv):
        """
        :param kv: a dict 
        
          for each key,value pair in dict kv
               set self.key = value
               
        """
        for key,value in kv.items():
            descriptor = self.__class__._getdescriptor(key)
            descriptor.__set__(self, value)
        
        
    def _remove(self, db=None, cascade = 'bnode', bnodeCheck=True):
        """remove all triples where this rdfSubject is the subject of the triple
        
        :param db: limit the remove operation to this graph
        :param cascade: must be one of:
        
                    * none --  remove none
                    * bnode -- (default) remove all unreferenced bnodes
                    * all -- remove all unreferenced bnode(s) AND uri(s)
        
        :param bnodeCheck: boolean 
        
                    * True -- (default) check bnodes and raise exception if there are
                      still references to this node
                    * False --  do not check.  This can leave orphaned object reference 
                      in triples.  Use only if you are resetting the value in
                      the same transaction
        """
        noderef = self.resUri            
        log.debug("Called remove on %s" % self)
        if not db:
            db = self.db
        
        # we cannot delete a bnode if it is still referenced, 
        # i.e. if it is the o of a s,p,o 
        if bnodeCheck:
            if isinstance(noderef ,BNode):
                for s,p,o in db.triples((None,None,noderef)):
                    raise RDFAlchemyError("Cannot delete a bnode %s becuase %s still references it" % (noderef.n3(), s.n3()))
        # determine an appropriate test for cascade decisions
        if cascade == 'bnode':
            #we cannot delete a bnode if there are still references to it
            def test(node):
                if isinstance(node,(URIRef,Literal)):
                    return False
                for s,p,o in db.triples((None,None,node)):
                    return False
                return True
        elif cascade == 'none':
            def test(node):
                return False
        elif cascade == 'all':
            def test(node):
                if isinstance(node, Literal):
                    return False
                for s,p,o in db.triples((None,None,node)):
                    return False
                return True
        else:
            raise AttributeError, "unknown cascade argument"
        for s,p,o in db.triples((noderef, None, None)):
            db.remove((s,p,o))
            if test(o):
                rdfSubject(o)._remove(db=db,cascade=cascade)

                
    def _rename(self, name, db=None):
        """rename a node """
        if not db:
            db = self.db
        if not (isinstance(name, (BNode,URIRef))):
            raise AttributeError, ("cannot rename to %s" % name)
        for s,p,o in db.triples((self.resUri,None,None)):
            db.remove((s, p, o))
            db.add((name, p, o))
        for s,p,o in db.triples((None,None,self.resUri)):
            db.set((s, p, name))
        self.resUri = name
        
        
    def _ppo(self,db=None):
        """Like pretty print...
        Return a 'pretty predicate,object' of self
        returning all predicate object pairs with qnames"""
        db = db or self.db
        for p,o in db.predicate_objects(self.resUri):
            print "%20s = %s"% (db.qname(p),str(o))
        print " "

    def md5_term_hash(self):
        """Not sure what good this method is but it's defined for
        rdflib.Identifiers so it's here for now"""
        return self.resUri.md5_term_hash()
        
    

