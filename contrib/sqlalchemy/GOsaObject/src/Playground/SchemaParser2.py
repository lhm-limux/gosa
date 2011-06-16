import xml.etree.ElementTree as etree


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
    
    def xml_to_dict(self, el):
        d={}
        if el.text:
            d[el.tag] = el.text
        else:
            d[el.tag] = {}
        
        children = el.getchildren()
            
        if children:
            d[el.tag] = map(self.xml_to_dict, children)
        return d
    
    def __parse(self, filename):
        tree = etree.parse('schema/Person-schema.xml')
        return(self.xml_to_dict(tree.getroot()))
       
    
    def load(self, filename):
        
        schema = self.__parse(filename)
        for id in schema['Classes']:
            
            className = properties = None
            for entry in id['Class']:
                if 'properties' in entry:
                    properties = entry['properties']
                
                if 'name' in entry:
                    className = entry['name']
                
            if className:
                self._registerClass(className, properties)

    def _registerClass(self, name, props):

        # The class wasn't defined yet, create a new metaclass for it.
        if not name in globals():

            # Create the class 
            class klass(GOsaBaseObject): 
                pass
            setattr(klass, '__name__', name)

            # populate the newly created class
            globals()[name] = klass

        # Update metaclass properties
        klass = globals()[name]
        if props:
            for key in props:
                
                # Normalise xml-generated dict.
                # Look for a better solution later 
                propAttrs = key['property']
                prop = {}
                for pEntry in propAttrs:
                    for n in pEntry:
                        prop[n] = pEntry[n]
                
                # Find a better mapping here later
                typemap = {}
                typemap['str'] = str()
                typemap['int'] = int()
                
                # Add the property to the class
                setattr(klass, prop['name'], typemap[prop['type']])
        

        


s = SchemaLoader()
s.load("schema/Person-schema.xml")

p = Person()



tim = Person()
tim.givenName = 'Horst'
tim.sn = 'Hackepeter'
tim.age = 2

print tim.givenName
print tim.sn
print tim.age