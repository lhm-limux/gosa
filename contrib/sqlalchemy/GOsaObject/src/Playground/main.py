from GOsaDBObject import GOsaDBObject, GOsaDBProperty, metadata
from SchemaParser import SchemaLoader
from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session

# Establish the database connection and open a session
metadata.bind = create_engine('mysql://admin@gosa-playground.intranet.gonicus.de/test', echo=False)
metadata.create_all()
session = Session()

# Load schema loader/object factory
factory = SchemaLoader()
factory.loadSchema('schema/Base-schema.xml')
factory.loadSchema('schema/Person-schema.xml')

# Populate metaclasses, maybe there is a nicer way to do this
for (cName, cClass) in factory.getClasses().items():
    globals()[cName] = cClass 

# Create a new object called father
father = Employee('cn=Father of Horst, ...')
father.givenName = 'The father!'
father.age = 1234
session.add(father.getObject())
session.commit()

# Create another object which references to the father object
tim = Person('cn=Horst Hackpeter, ist voll toll')
tim.givenName = 'Horst'
tim.sn = 'Hackepeter'
tim.age = 2
tim.parent = father.getObject()
tim.notes = ['tester', '44', 55, father.getObject()]
session.add(tim.getObject())
session.commit()

# Walk through database that match 'Horst'
for entry in session.query(GOsaDBObject).filter(GOsaDBObject.properties.any(GOsaDBProperty.value == u'Horst')).all():
    entry = factory.toObject(entry)

    print '-' * 80
    print "Object is of type: %s" % entry.type
    print "Age is: %i" % entry.age, type(entry.age)
    print "Parent is: %s" % str(entry.parent)
    print "He has some notes", entry.notes
    if entry.parent:
        print "The father is: %s" % str(factory.toObject(entry.parent).givenName)
    #entry.delete()
    #entry.getSession().commit()




