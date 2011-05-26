class RDFAlchemyError(Exception):
    """Generic error class."""


class RDFAbstractClassError(RDFAlchemyError):
    """Cannot generate instances of Abstract Classes"""


class SPARQLError(Exception):
    """Base SPARQL Error"""

class MalformedQueryError(SPARQLError):
    """Query Syntax Error for SPARQL RDQL etc
    
    In Sesame:
       org.openrdf.query.MalformedQueryException"""

class QueryEvaluationError(SPARQLError):
    """Query Evaluation Error reported by Server
    
    In Sesame:
      org.openrdf.query.QueryEvaluationException"""

