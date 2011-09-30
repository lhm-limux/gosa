"""
Prepare:

# easy_install RelStorage


From the docs:

ZODB databases can be accessed from multithreaded Python programs. The Storage
and DB instances can be shared among several threads, as long as individual
Connection instances are created for each thread.
"""
import ZODB.config
import transaction

db = ZODB.config.databaseFromURL('client.conf')
conn = db.open()
root = conn.root()

# Store some things in the root
#root['list'] = ['a', 'b', 1.0, 3]
#root['dict'] = {'a':1, 'b':4}

# Commit the transaction
#transaction.commit()

print root['list']
print root['dict']
