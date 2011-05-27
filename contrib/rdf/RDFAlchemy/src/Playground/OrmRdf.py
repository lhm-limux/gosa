from rdfalchemy import rdfSubject, rdfSingle, rdfContainer
from rdfalchemy.orm import mapper
from rdflib import Namespace, ConjunctiveGraph
from rdflib import plugin
from rdflib.store import Store

# Create a GOsa namespace, normally URIs are used here, but
# we do not represent Web-Site data here.
NS = Namespace('GOsa-Device#')
    
# Open database connection 
openstr= 'db=test,host=gosa-playground,user=admin'
store = plugin.get('MySQL', Store)('test')
store.open(openstr,create=False)
rdfSubject.db = ConjunctiveGraph(store)
 
# Define classes
class Partition(rdfSubject):
    rdf_type = NS.Partition
    type = rdfSingle(NS.fsType)
    size = rdfSingle(NS.partitionSize)
    bootable = rdfSingle(NS.boolean)
 
class Disk(rdfSubject):
    rdf_type = NS.Disk
    name = rdfSingle(NS.name)
    partitions = rdfContainer(NS.knowsL, range_type=NS.Partition)
    partition = rdfSingle(NS.Partition, range_type=NS.Partition)

class Device(rdfSubject):
    rdf_type = NS.Device
    uuid = rdfSingle(NS.uuid)
    name = rdfSingle(NS.deviceName)
    disks = rdfContainer(NS.knowsL, range_type=NS.Disk)

mapper()

# Create and add Objects to the DB 
p = Partition(type='ext3', size='1GB', bootable='True')
d = Disk(name='disk1', partitions=[p], partition=p)
dev = Device(uuid='device2', name='Herbert', disks=[d])
dev.db.commit()

# Receive object from DB
dev = Device.get_by(uuid='device2')

# Dynamic property addition
Device.location = rdfSingle(NS.location)

#dev.location = 'Arnsberg'
#dev.db.commit()

print dev.location
print dev.disks
print dev.disks[0].partitions
print dev.disks[0].partitions[0].size
print dev.disks[0].partition.size
