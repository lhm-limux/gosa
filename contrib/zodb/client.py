"""
Prepare:

# easy_install RelStorage


From the docs:

ZODB databases can be accessed from multithreaded Python programs. The Storage
and DB instances can be shared among several threads, as long as individual
Connection instances are created for each thread.

TODO:
 * indexing
 * btrees
"""
import ZODB.config
import transaction
from BTrees.OOBTree import OOBTree

db = ZODB.config.databaseFromURL('client.conf')
conn = db.open()
root = conn.root()

#data = OOBTree()
#data['members'] = {'cajus': 'pollmeier', 'fabian': 'hickert'}
#root['objects'] = data
#
#transaction.commit()

print root['objects']['members']
