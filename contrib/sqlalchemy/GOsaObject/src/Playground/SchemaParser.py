

schema = {
    'name': 'Person',
    'values': 
        {
            'givenName': 
            {
                'type': str,
                'length': None,
            },
            'age': 
            {
                'type': int,
                'length': None,
            }
        }
    }

schemaUpdate = {
    'name': 'Person',
    'values':
        {
            'sn':   # < -- Added 
            {
                'type': str,
                'length': None,
            },
            'age': # < -- Altered to type str
            {
                'type': str,
                'length': None,
            }
        }
    }





class GOsaBaseObject(object):

    def __setattr__(self, name, value):
        if not hasattr(self, name):
            raise Exception("There is no such property '%s' for class '%s'." % (name, type(self)))
            return

        if type(value) != type(getattr(self, name)):
            raise Exception("Invalid type given '%s', expected '%s'" % (type(value), type(getattr(self, name))))
        else:
            #setattr(self, name, value)
            self.__dict__[name] = value


class SchemaLoader(object):
    
    def load(self, schema):

        # The class wasn't defined yet, create a new metaclass for it.
        if not schema['name'] in globals():

            # Create the class 
            class klass(GOsaBaseObject): 
                pass
            setattr(klass, '__name__', schema['name'])

            # populate the newly created class
            globals()[schema['name']] = klass

        # Update metaclass properties
        klass = globals()[schema['name']]
        for key in schema['values']:
            setattr(klass, key, schema['values'][key]['type']())
        

        


s = SchemaLoader()
s.load(schema)
s.load(schemaUpdate)

tim = Person()
tim.givenName = 'Horst'
tim.sn = 'Hackepeter'
tim.age = '2'

print tim.givenName
print tim.sn
print tim.age