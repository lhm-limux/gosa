from rdfalchemy import rdfSubject, rdfSingle, rdfContainer, URIRef
from rdfalchemy.orm import mapper
from rdflib import Namespace, ConjunctiveGraph
from rdflib import plugin
from rdflib.store import Store

# Enable logging & Debug
import logging
log = logging.getLogger()
log.addHandler(logging.StreamHandler())
log.setLevel(logging.ERROR)

# Create a GOsa namespace, normally URIs are used here, but
# we do not represent Web-Site data here.
GOSA = Namespace('GOsa-Device#')
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
XS = Namespace("http://www.w3.org/2001/XMLSchema#")

# Open database connection 
openstr= 'db=test,host=gosa-playground,user=admin'
store = plugin.get('MySQL', Store)('test')
store.open(openstr,create=False)
rdfSubject.db = ConjunctiveGraph(store)


# 
rdfSubject.db.bind("RDF", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
rdfSubject.db.bind("XS", "http://www.w3.org/2001/XMLSchema#")

## To print out all registered serializers, stores, ...
#for entry in plugin._kinds:
#    print entry
#    for value in  plugin._kinds[entry]:
#        print "\t", value


#rdfSubject.db = ConjunctiveGraph()
#rdfSubject.db.bind("owl", "http://www.w3.org/2002/07/owl#")
 
# Define classes
class Partition(rdfSubject):
    rdf_type = GOSA.Partition
    type = rdfSingle(RDF.Property)
    size = rdfSingle(RDF.Property)
    bootable = rdfSingle(RDF.Property)
 
class Disk(rdfSubject):
    rdf_type = GOSA.Disk
    name = rdfSingle(GOSA.name)
    partitions = rdfContainer(RDF.Property, range_type=GOSA.Partition)
    partition = rdfSingle(RDF.PropertyL, range_type=GOSA.Partition)

class Device(rdfSubject):
    rdf_type = GOSA.Device
    uuid = rdfSingle(RDF.Property)
    name = rdfSingle(RDF.Property)
    disks = rdfContainer(RDF.PropertyL, range_type=GOSA.Disk)

mapper()



## Create and add Objects to the DB 
#p = Partition(URIRef('___partition'), type='ext3', size='1GB', bootable='True')
#d = Disk(URIRef('___disk'), name='disk1', partitions=[p], partition=p)
#dev = Device(URIRef('___device'), uuid='device2', name='Herbert', disks=[d])
#dev.db.commit()


# Create a device
uuid = "9374-32451-12-2312312" # not a valid uuid, i know
device = Device(URIRef(uuid), name='Garnele')
device.uuid = uuid

# Create a disk
disk = Disk(URIRef(uuid + 'sda'))
disk.name = 'sda'

# Create a partition
partition = Partition(URIRef(uuid + 'sda' + '/')) 
partition.size='400MB'

# Combine classes
device.disks = [disk]
disk.partition = partition
disk.partitions = [partition]




# Receive object from DB
dev = Device.get_by(uuid='9374-32451-12-2312312')

# Dynamic property addition
Device.location = rdfSingle(GOSA.location)
dev.location = 'Arnsberg'
dev.db.commit()

print dev.disks
print dev.disks[0].partitions
print dev.disks[0].partitions[0].size
print dev.disks[0].partition.size

print len(rdfSubject.db)

#print rdfSubject.db.serialize(format="xml")
#print rdfSubject.db.serialize(format="n3")
#print rdfSubject.db.serialize(format="rdf")
#print rdfSubject.db.serialize(format="rdf/xml")
