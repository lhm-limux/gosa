from rdfalchemy import rdfSubject, rdfSingle
from rdflib import Namespace, ConjunctiveGraph
from rdflib import plugin
from rdflib.store import Store

import logging
log = logging.getLogger()

#log.addHandler(logging.StreamHandler())
#log.setLevel(logging.DEBUG)

OV = Namespace('http://owl.openvest.org/2005/10/Portfolio#')
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

# Create Database connection on our own.
openstr= 'db=test,host=gosa-playground,user=admin'
store = plugin.get('MySQL', Store)('test')
store.open(openstr,create=False)
db = ConjunctiveGraph(store)
rdfSubject.db = db
 
class Company(rdfSubject):
    rdf_type = OV.Company
    symbol = rdfSingle(OV.symbol,'symbol')
    sy = rdfSingle(None)
    cik = rdfSingle(OV.secCik,'cik')
    companyName = rdfSingle(OV.companyName)
    address = rdfSingle(VCARD.adr)

#ibm = Company(symbol='IBM')


c = Company.get_by(symbol='IBM')
#c.companyName = 'Schinken'
#Company.db.commit()

print c.symbol
print c.companyName;
