from n3_2 import testN3Store,testN3,implies
from rdflib.Graph import QuotedGraph
from rdflib import *
configString="user=test,password=,host=localhost,db=test"


if __name__=='__main__':
    testN3Store('PostgreSQL',configString)
    #testRegex()
    #profileTests()
