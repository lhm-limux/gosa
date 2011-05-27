from rdflib.Graph import ConjunctiveGraph as Graph
from rdflib import plugin
from rdflib.store import Store
from rdflib import Namespace
from rdflib import Literal
from rdflib import URIRef

default_graph_uri = "http://rdflib.net/rdfstore"
configString = "host=gosa-playground,user=admin,password=,db=test"

# Get the mysql plugin. You may have to install the python mysql libraries
store = plugin.get('MySQL', Store)('rdfstore')
store.open(configString,create=False)

# There is a store, use it
graph = Graph(store, identifier = URIRef(default_graph_uri))

print "Triples in graph before add: ", len(graph)

# Now we'll add some triples to the graph & commit the changes
rdflib = Namespace('http://rdflib.net/test/')
graph.add((rdflib['pic:1'], rdflib['name'], Literal('Jane & Bob')))
graph.add((rdflib['pic:2'], rdflib['name'], Literal('Squirrel in Tree')))
graph.commit()




