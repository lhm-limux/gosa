from rdfalchemy import rdfSubject, engine
from rdflib import Namespace

import logging
log = logging.getLogger()

#log.addHandler(logging.StreamHandler())
#log.setLevel(logging.DEBUG)

OV = Namespace('http://owl.openvest.org/2005/10/Portfolio#')
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

# ! DOES not work initially - create isn't handled for MySql backends
db = engine.create_engine('mysql://admin@gosa-playground/test', create=True);
rdfSubject.db = db

