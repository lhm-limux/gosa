from GOsaObject import *
from SchemaParser2 import *
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session

# Establish the database connection and open a session
metadata.bind = create_engine('mysql://admin@gosa-playground.intranet.gonicus.de/test', echo=False)
metadata.create_all()
session = Session()

# Load schema
factory = SchemaLoader(session)
factory.loadSchema('schema/Person-schema.xml')

# Populate metaclasses
for (cName, cClass) in factory.getClasses().items():
    globals()[cName] = cClass 


#p = Person('test')




#tim = Person('cn=Horst Hackpeter, ist voll toll')
#tim.givenName = 'Horst'
#tim.sn = 'Hackepeter'
#tim.age = 2


#print tim.givenName
#print tim.sn
#print tim.age

#tim.add()
#Person.session.commit()

for entry in session.query(GOsaObject).filter(GOsaObject.properties.any(GOsaProperty.value == u'Horst')).all():
    entry = factory.load(entry)
    print entry.age
    print entry.gosa_object
    entry.age = entry.age + 1
    entry.add()
    entry.getSession().commit()




