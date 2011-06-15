from GOsaObject import GOsaObject, GOsaProperty, metadata
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session

# Establish the database connection and open a session
metadata.bind = create_engine('mysql://admin@gosa-playground.intranet.gonicus.de/test', echo=False)
metadata.create_all()
session = Session()


# Query existing objects with a name
entry = None




for entry in session.query(GOsaObject).filter(GOsaObject.properties.any(GOsaProperty.value== u'Hickert')).all():
    
    print entry
    print entry.name, ',' , entry['givenName']
    print entry['addressObject']['mail']
    print entry['alternateAddresses']
    print entry['list']    
 
    o = GOsaObject(u'Hubert')
    
    entry[u'list'] = [u'test', u'herbert', 3, o]

    session.add(entry)
    session.commit()

 
if not entry:

    address = GOsaObject(name=u'Hickerts address')
    address['mail'] = u'hickert@gonicus.de'

    o = GOsaObject(name=u'User hickert')
    o['name'] = u'Hickert'
    o['givenName'] = u'Fabian'
    o['objectClass'] = u'person'
    o['addressObject'] = address
    o['alternateAddresses'] = [address]

    o['list'] = ['a', 'b'] 
    
    session.add(o)
    session.commit()
    

