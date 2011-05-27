#!/usr/bin/env python2.6

from sparta import ThingFactory
from rdflib.Graph import Graph

# Create the graph
store = Graph()

# Bind schema definition using abbreviations.
store.bind("xs", "http://www.w3.org/2001/XMLSchema#")
store.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
store.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
store.bind("owl", "http://www.w3.org/2002/07/owl#")

# Create the classes 
store.bind("disk", "http://www.example.com/contact#")
store.bind("partition", "http://www.example.com/partition#")

# Create the thing default class
Thing = ThingFactory(store)

Thing("disk_size", rdf_type=[Thing("owl_FunctionalProperty")])
Thing("disk_size", rdfs_range=[Thing("xs_short")])
Thing("disk_name", rdf_type=[Thing("owl_FunctionalProperty")])
Thing("disk_partitions", rdf_type=[Thing("owl_FunctionalProperty")])

Thing("partition_size", rdf_type=[Thing("owl_FunctionalProperty")])
Thing("partition_size", rdfs_type=[Thing("xs_short")])
Thing("partition_mountPoint", rdf_type=[Thing("owl_FunctionalProperty")])

# Create a partition object
part = Thing('partition_part')
part.partition_size = 400
part.partition_mountPoint = '/'

# Create a disk object
sda = Thing('disk_sda')
sda.disk_name = 'sda'
sda.disk_size = 300
sda.disk_partitions = [part]

print store.serialize(format="xml")

