import ZODB.config
import transaction

db = ZODB.config.databaseFromURL('client.conf')
conn = db.open()
root = conn.root()

## Store some things in the root
#root['list'] = ['a', 'b', 1.0, 3]
#root['dict'] = {'a':1, 'b':4}
#
## Commit the transaction
#transaction.commit()

print root['list']
print root['dict']
