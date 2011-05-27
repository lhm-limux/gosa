
from rdflib import Literal, BNode, Namespace, URIRef

# this has the rdfSubject stuff and the Fresnel stuff
from rdfalchemy import *


ov = Namespace("http://owl.openvest.org/2005/10/Portfolio#")
edgarns = Namespace('http://www.sec.gov/Archives/edgar')

class Company(rdfSubject):
    rdf_type = ov.Company
    symbol = rdfSingle(ov.symbol,)
    cik = rdfSingle(ov.secCik,'cik')
    companyName = rdfSingle(ov.companyName,'companyName')
    stockDescription = rdfSingle(ov.stockDescription,'stockDescription')
    stock = rdfMultiple(ov.hasIssue)
        
                                                                                                                                        

class EdgarFiling(rdfSubject):
    rdf_type = edgarns.xbrlFiling
    accessionNumber = rdfSingle(edgarns.accessionNumber)
    companyName = rdfSingle(edgarns.companyName)
    filingDate = rdfSingle(edgarns.filingDate)
    formType = rdfSingle(edgarns.formType)
                                                                                                                                                                                                                                                                                                                                                                   
