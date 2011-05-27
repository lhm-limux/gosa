from rdfalchemy import URIRef , Literal, BNode, RDF
from rdfalchemy.exceptions import MalformedQueryError, QueryEvaluationError
from rdfalchemy.sparql.parsers import _XMLSPARQLHandler,_JSONSPARQLHandler

from rdflib import ConjunctiveGraph
from rdflib.syntax.parsers.ntriples import NTriplesParser

from urllib2 import urlopen, Request, HTTPError
from urllib import urlencode

import re
import logging

__all__=["SPARQLGraph",]

log=logging.getLogger(__name__)

class DumpSink(object):
   def __init__(self):
      self.length = 0

   def triple(self, s, p, o):
      self.length += 1
      self._triple=(s,p,o)

   def get_triple(self):
       return self._triple


class SPARQLGraph(object):
    """provides (some) rdflib api via http to a SPARQL endpoint
    gives 'read-only' access to the graph
    constructor takes http endpoint and repository name
    e.g.  SPARQLGraph('http://localhost:2020/sparql')"""
    
    parsers = {'xml': _XMLSPARQLHandler, 'json': _JSONSPARQLHandler}
    
    def __init__(self, url, context=None):
        self.url = url
        self.context=context

    def construct(self, strOrTriple, initBindings={}, initNs={}):
        """
        Executes a SPARQL Construct
        :param strOrTriple: can be either
        
          * a string in which case it it considered a CONSTRUCT query
          * a triple in which case it acts as the rdflib `triples((s,p,o))`
        
        :param initBindings:  A mapping from a Variable to an RDFLib term (used as initial bindings for SPARQL query)
        :param initNs:  A mapping from a namespace prefix to a namespace
        
        :returns: an instance of rdflib.ConjuctiveGraph('IOMemory')
        """
        if isinstance(strOrTriple, str):
            query = strOrTriple
            if initNs:
                prefixes = ''.join(["prefix %s: <%s>\n"%(p,n) for p,n in initNs.items()])
                query = prefixes + query
        else:
            s,p,o = strOrTriple
            t='%s %s %s'%((s and s.n3() or '?s'),(p and p.n3() or '?p'),(o and o.n3() or '?o'))
            query='construct {%s} where {%s}'%(t,t)
        query = dict(query=query)
        
        url = self.url+"?"+urlencode(query)
        req = Request(url)
        req.add_header('Accept','application/rdf+xml')
        log.debug("Request url: %s\n  with headers: %s" % (req.get_full_url(), req.header_items()))        
        subgraph = ConjunctiveGraph('IOMemory')
        subgraph.parse(urlopen(req))
        return subgraph
        
    def triples(self, (s,p,o), method='CONSTRUCT'):
        """
        :returns: a generator over triples matching the pattern
        :param method: must be 'CONSTRUCT' or 'SELECT'
        
             * CONSTRUCT calls CONSTRUCT query and returns a Graph result 
             * SELECT calls a SELECT query and returns an interator streaming over the results
        
        Use SELECT if you expect a large result set or may consume less than the entire result"""
        if method == 'CONSTRUCT':
            return self.construct((s,p,o)).triples((None,None,None))
        elif method == 'SELECT':
            pattern = "%s %s %s"%((s and s.n3() or '?s'),(p and p.n3() or '?p'),(o and o.n3() or '?o'))
            query = "select ?s ?p ?o where { %s . }" % pattern
            return self.query(query)
        else:
            raise ValueError, "Unknown method: %s"%(method)
    
    def __iter__(self):
        """Iterates over all triples in the store"""
        return self.triples((None, None, None))

    def __contains__(self, triple):
        """Support for 'triple in graph' syntax"""
        for triple in self.triples(triple):
            return 1
        return 0
        
    def subjects(self, predicate=None, object=None):
        """A generator of subjects with the given predicate and object"""
        for s, p, o in self.triples((None, predicate, object)):
            yield s

    def predicates(self, subject=None, object=None):
        """A generator of predicates with the given subject and object"""
        for s, p, o in self.triples((subject, None, object)):
            yield p

    def objects(self, subject=None, predicate=None):
        """A generator of objects with the given subject and predicate"""
        for s, p, o in self.triples((subject, predicate, None)):
            yield o

    def subject_predicates(self, object=None):
        """A generator of (subject, predicate) tuples for the given object"""
        for s, p, o in self.triples((None, None, object)):
            yield s, p

    def subject_objects(self, predicate=None):
        """A generator of (subject, object) tuples for the given predicate"""
        for s, p, o in self.triples((None, predicate, None)):
            yield s, o

    def predicate_objects(self, subject=None):
        """A generator of (predicate, object) tuples for the given subject"""
        for s, p, o in self.triples((subject, None, None)):
            yield p, o


    def value(self, subject=None, predicate=RDF.value, object=None, default=None, any=True):
        """Get a value for a pair of two criteria

        Exactly one of subject, predicate, object must be None. Useful if one
        knows that there may only be one value.

        It is one of those situations that occur a lot, hence this *macro* like utility

        :param  subject, predicate, object: exactly one must be None
        :param default: value to be returned if no values found
        :param any:     if more than one answer return **any one** answer, otherwise `raise UniquenessError`
        """
        retval = default

        if (subject is None and (predicate is None or object is None)) or \
                (predicate is None and object is None):
            return None
        
        if object is None:
            values = self.objects(subject, predicate)
        if subject is None:
            values = self.subjects(predicate, object)
        if predicate is None:
            values = self.predicates(subject, object)

        try:
            retval = values.next()
        except StopIteration, e:
            retval = default
        else:
            if any is False:
                try:
                    next = values.next()
                    msg = ("While trying to find a value for (%s, %s, %s) the "
                           "following multiple values where found:\n" %
                           (subject, predicate, object))
                    triples = self.triples((subject, predicate, object))
                    for (s, p, o) in triples:
                        msg += "(%s, %s, %s)\n" % (s, p, o)
                    raise exceptions.UniquenessError(msg)
                except StopIteration, e:
                    pass
        return retval

    def label(self, subject, default=''):
        """Query for the RDFS.label of the subject

        Return default if no label exists
        """
        if subject is None:
            return default
        return self.value(subject, RDFS.label, default=default, any=True)

    def comment(self, subject, default=''):
        """Query for the RDFS.comment of the subject

        Return default if no comment exists
        """
        if subject is None:
            return default
        return self.value(subject, RDFS.comment, default=default, any=True)

    def items(self, list):
        """Generator over all items in the resource specified by list

        list is an RDF collection.
        """
        while list:
            item = self.value(list, RDF.first)
            if item:
                yield item
            list = self.value(list, RDF.rest)
            
    def transitive_objects(self, subject, property, remember=None):
       """Transitively generate objects for the `property` relationship

       Generated objects belong to the depth first transitive closure of the
       `property` relationship starting at `subject`.
       """
       if remember is None:
           remember = {}
       if subject in remember:
           return
       remember[subject] = 1
       yield subject
       for object in self.objects(subject, property):
           for o in self.transitive_objects(object, property, remember):
               yield o
              
    def transitive_subjects(self, predicate, object, remember=None):
        """Transitively generate objects for the `property` relationship

        Generated objects belong to the depth first transitive closure of the
        `property` relationship starting at `subject`.
        """
        if remember is None:
            remember = {}
        if object in remember:
            return
        remember[object] = 1
        yield object
        for subject in self.subjects(predicate, object):
            for s in self.transitive_subjects(predicate, subject, remember):
                yield s
           
    def qname(self,uri):
        """turn uri into a qname given self.namespaces
        This works for rdflib graphs and is defined for SesameGraph
        but is **not** part of SPARQLGraph"""
        raise NotImplementedError
        

    def query(self, strOrQuery, initBindings={}, initNs={}, resultMethod="xml",processor="sparql",rawResults=False):
        """
        Executes a SPARQL query against this Graph
        
        :param strOrQuery: Is either a string consisting of the SPARQL query 
        :param initBindings: *optional* mapping from a Variable to an RDFLib term (used as initial bindings for SPARQL query)
        :param initNs: optional mapping from a namespace prefix to a namespace
        :param resultMethod: results query requested (must be 'xml' or 'json') 
         xml streams over the result set and json must read the entire set  to succeed 
        :param processor: The kind of RDF query (must be 'sparql' or 'serql')
        :param rawResults: If set to `True`, returns the raw xml or json stream rather than the parsed results.
        """
        log.debug("Raw Query: %s"%(strOrQuery))
        prefixes = ''.join(["prefix %s: <%s>\n"%(p,n) for p,n in initNs.items()])
        if initBindings :
            query=self._processInitBindings(strOrQuery,initBindings)
        else:
            query = strOrQuery
        query = prefixes + query
        log.debug("Prepared Query: %s"%(query))
        query = dict(query=query,queryLn=processor)
        url = self.url+"?"+urlencode(query)
        parser = self.getParser(resultMethod, url)

        return rawResults and parser.stream or parser.parse() 
        
    def getParser(self, resultMethod, url):
        try:
            return self.parsers[resultMethod](url)
        except LookupError:
            raise ValueError , "Invalid resultMethod: %s" % resultMethod
        except HTTPError, e:
            if  e.code == 400: # and e.msg.startswith('Parse_error'):
                errmsg = e.fp.read()
                submsg = re.search("<pre>(.*)</pre>",errmsg,re.MULTILINE|re.DOTALL)
                submsg = submsg and submsg.groups()[0]
                raise MalformedQueryError, submsg or errmsg
            raise HTTPError, e 
            
    @classmethod
    def _processInitBindings(cls, query, initBindings):
        """_processInitBindings will convert a query by replacing the Variables
        
        >>> SPARQLGraph._processInitBindings('SELECT ?x { ?x ?y ?z }', {'z' : 'hi'})
        u'SELECT ?x { ?x ?y "hi" }'
        >>> SPARQLGraph._processInitBindings('SELECT ?x { ?x <http://example/?z=1> ?z }', {'z' : 'hi'})
        u'SELECT ?x { ?x <http://example/?z=1> "hi" }'

        :param query: the query to process
        :param initBindings: a dict of variable to value"""
        # TODO: what if a BNode is the val in the bindings
        #       should it be left at a ?var or converted to a _:bnode ???
        def varval(x):
            var =  x.groups()[0]
            if var in initBindings:
                val = initBindings[var]
                try:
                    return val.n3()
                except:
                    return Literal(val).n3()
            return x.group()
        
        re_qvars = re.compile('(?<=[\]\.\;\{\s])\?(%s)'%('|'.join(initBindings.keys())))
        return re_qvars.sub(varval,query)
    

    def describe(self, s_or_po, initBindings={}, initNs={}):
        """
        Executes a SPARQL describe of resource
        
        :param s_or_po:  is either
        
          * a subject ... should be a URIRef
          * a tuple of (predicate,object) ... pred should be inverse functional
          * a describe query string
          
        :param initBindings: A mapping from a Variable to an RDFLib term (used as initial bindings for SPARQL query)
        :param initNs: A mapping from a namespace prefix to a namespace
        """
        if isinstance(s_or_po, str):
            query = s_or_po
            if initNs:
                prefixes = ''.join(["prefix %s: <%s>\n"%(p,n) for p,n in initNs.items()])
                query = prefixes + query
        elif isinstance(s_or_po, URIRef) or isinstance(s_or_po, BNode):
            query = "describe %s" % (s_or_po.n3())
        else:
            p,o = s_or_po
            query = "describe ?s where {?s %s %s}"%(p.n3(),o.n3())
        query = dict(query=query)
        
        url = self.url+"?"+urlencode(query)
        req = Request(url)
        req.add_header('Accept','application/rdf+xml')
        log.debug("opening url: %s\n  with headers: %s" % (req.get_full_url(), req.header_items()))
        subgraph = ConjunctiveGraph()
        subgraph.parse(urlopen(req))
        return subgraph
