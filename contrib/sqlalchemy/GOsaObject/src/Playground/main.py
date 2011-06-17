from GOsaDBObject import *
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


father = Employee('cn=Father of Horst, ...')
father.givenName = 'The father!'
father.add()
Employee.session.commit()

for i in range(1, 10):
    tim = Person('cn=Horst Hackpeter, ist voll toll')
    tim.givenName = 'Horst'
    tim.sn = 'Hackepeter'
    tim.age = 2
    tim.parent = father.gosa_object
    tim.notes = ['tester', '44', 55, father.gosa_object]
    tim.add()
    
Person.session.commit()

for entry in session.query(GOsaDBObject).filter(GOsaDBObject.properties.any(GOsaDBProperty.value == u'Horst')).all():
    entry = factory.toObject(entry)
    print entry.age
    print entry.parent
    print entry.notes
    if entry.parent:
        print factory.toObject(entry.parent)
        print factory.toObject(entry.parent).givenName
    #entry.delete()
    #entry.getSession().commit()




