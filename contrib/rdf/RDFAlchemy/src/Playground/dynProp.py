from rdfalchemy import rdfSubject, rdfSingle, rdfContainer, RDFS
from rdfalchemy.orm import mapper
from rdflib import Namespace, ConjunctiveGraph
from rdflib import plugin
from rdflib.store import Store
from  rdfalchemy.descriptors import rdfLocale

GOSA = Namespace('http://gosa-playground/Rdf/gosa-ng.rdfs#')
 
import logging
log=logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
 
# Open database connection 
openstr= 'db=test,host=gosa-playground,user=admin'
store = plugin.get('MySQL', Store)('test')
store.open(openstr,create=False)
db = ConjunctiveGraph(store)
rdfSubject.db = db

# Define classes
class Partition(rdfSubject):
    rdf_type = GOSA.Partition
    type = rdfSingle(GOSA.fsType)
    size = rdfSingle(GOSA.partitioGOSAize)
    bootable = rdfSingle(GOSA.boolean)
 
class Disk(rdfSubject):
    rdf_type = GOSA.Disk
    name = rdfSingle(GOSA.name)
    partitions = rdfContainer(GOSA.knowsL, range_type=GOSA.Partition)
 
class Device(rdfSubject):
    rdf_type = GOSA.Device
    uuid = rdfSingle(GOSA.uuid)
    name = rdfSingle(GOSA.deviceName)
    disks = rdfContainer(GOSA.knowsL, range_type=GOSA.Disk)


mapper()

# Dynamically add property
Disk.le = rdfLocale(RDFS.label, 'en')

# Create disk
d = Disk(GOSA.Disk)

# Create and add Objects to the DB 
p = Partition(type='ext3', size='1GB', bootable='True')
d = Disk(name='disk1', partitions=[p])
dev = Device(uuid='device', name='Herbert', disks=[d])
dev.db.commit()

# Receive object from DB
dev = Device.get_by(uuid='device')

print dev.disks
print dev.disks[0].partitions
print dev.disks[0].partitions[0].size





