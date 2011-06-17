from GOsaObject import *
from SchemaParser import *
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


for i in range(1,10):
    tim = Person('cn=Horst Hackpeter, ist voll toll')
    tim.givenName = 'Horst'
    tim.sn = 'Hackepeter'
    tim.age = 2
    tim.add()
    
Person.session.commit()

for entry in session.query(GOsaObject).filter(GOsaObject.properties.any(GOsaProperty.value == u'Horst')).all():
    entry = factory.load(entry)
    print entry.gosa_object.name
    print entry.age
    entry.delete()
    entry.getSession().commit()




