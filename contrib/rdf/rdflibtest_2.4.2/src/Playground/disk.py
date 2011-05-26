import rdflib
from rdflib.Graph import ConjunctiveGraph as Graph
from rdflib import plugin
from rdflib.store import Store, NO_STORE, VALID_STORE
from rdflib import Namespace
from rdflib import Literal
from rdflib import URIRef, BNode

default_graph_uri = "http://rdflib.net/rdfstore"
configString = "host=gosa-playground,user=admin,password=,db=test"

# Get the mysql plugin. You may have to install the python mysql libraries
store = plugin.get('MySQL', Store)('rdfstore')
store.open(configString,create=False)
    
# There is a store, use it
graph = Graph(store, identifier = URIRef(default_graph_uri))

disk = BNode('sda1')
partition1 = BNode('part1')
device = BNode('0000-9273627-23223-111')

foaf=Namespace("GOsa-ng:")
initNs = dict(foaf=foaf)

# Do not create things twice
if not len(graph.query('SELECT ?v WHERE { ?v foaf:name "disk1" }', initNs=initNs)):
    graph.add((disk, foaf.hasPartition, Literal(partition1)))
    graph.add((disk, foaf.name, Literal('disk1')))
    graph.add((disk, foaf.fsType, Literal('ext3')))
    graph.add((disk, foaf.mountPoint, Literal('/home')))
    graph.add((partition1, foaf.diskSize, Literal('300MB')))
    graph.commit()
    

for row in graph.query('SELECT ?v ?name ?partition ?fsType '
                       'WHERE { '
                                '?v foaf:name ?name . ' 
                                '?v foaf:hasPartition ?partition . '
                                '?v foaf:fsType ?fsType . '
                                '} ', initNs=initNs ):
    print "Disk '%s(%s)' has partitions '%s' '%s'" % row
    
    for part_row in graph.query('select ?v ?p WHERE { ?v foaf:diskSize ?p }',
                   initNs=dict(foaf=Namespace("http://xmlns.com/foaf/0.1/"))):
        print "Partition '%s' has size '%s'" % part_row


# display the graph in RDF/XML
print graph.serialize()

print graph.serialize(format="nt")

