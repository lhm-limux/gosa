from rdflib import URIRef, BNode, Namespace, RDF, RDFS
from Literal import Literal
from rdfSubject import rdfSubject
from rdfsSubject import rdfsSubject,rdfsClass
from descriptors import *

from engine import create_engine, engine_from_config

# if users don't use logging they could see a 
# a confusing "No Handler could be found" warning
# this will mute that warning
import logging

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

log = logging.getLogger(__name__)
log.addHandler(NullHandler())

__version__="0.2b2"