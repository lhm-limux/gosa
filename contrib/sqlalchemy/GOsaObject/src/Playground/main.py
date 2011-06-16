from GOsaObject import GOsaObject, GOsaProperty, metadata
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session

# Establish the database connection and open a session
metadata.bind = create_engine('mysql://admin@gosa-playground.intranet.gonicus.de/test', echo=False)
metadata.create_all()
session = Session()


# Query existing objects with a name
entry = None




if False:
   
    c = GOsaObject(u'GONICUS GmbH')
    c['address'] = u'Moehnestrasse 11-17'
    
    for i in range(1,1000):
        o = GOsaObject(u'User %s' % str(i))
        o['username'] = u'Username %s' % str(i)
        o['company'] = c
        o['relationships'] = [c]
    
        session.add(o)
        session.commit()



for entry in session.query(GOsaObject).filter(GOsaObject.properties.any(GOsaProperty.key== u'username')).all():
    
    print entry
    print entry.name
    print entry['company']
    #print entry['relationships']
 
