from GOsaDBObject import GOsaDBObject
import xml.etree.ElementTree as etree


class GOsaBaseObject(object):

    session = None
    gosa_object = None

    def __init__(self, uri = None, gosa_object=None):
        
        if gosa_object:
            self.gosa_object = gosa_object
        else:
            self.gosa_object = GOsaDBObject(unicode(uri))
            self.gosa_object['type'] = self.__class__.__name__

    def add(self):
        self.session.add(self.gosa_object)

    def delete(self):
        self.session.delete(self.gosa_object)

    def getSession(self):
        return(self.session)
    
    def __getattribute__(self, name):

        db_props = object.__getattribute__(self, '_db_properties')
        if name not in db_props:
            return object.__getattribute__(self, name)
        
        else:
            v = object.__getattribute__(self, name)
            if isinstance(v, GOsaDBObject):
                return self.gosa_object[name]
            else:
                old_type = type(v)
                val = self.gosa_object[name]
                if val == None:
                    return old_type()
                else:
                    return old_type(self.gosa_object[name])

    def __setattr__(self, name, value):
        
        # Do not save base class properties in the backend.
        #if name in dir(GOsaBaseObject):
        db_props = object.__getattribute__(self, '_db_properties')
        if name in db_props:

            # Check if given value matches the requested types 
            if (type(value) != type(getattr(self, name))) and not issubclass(type(value), GOsaDBObject):
                raise Exception("Invalid type given '%s', expected '%s'" % (type(value), type(getattr(self, name))))
            else:
                object.__setattr__(self, name, value)
                self.gosa_object[name] = value
                return
        
        # Check if the given property was defined in the xml schema
        if not hasattr(self, name):
            raise Exception("There is no such property '%s' for class '%s'." % (name, type(self)))
        else:
            object.__setattr__(self, name, value) 

class SchemaLoader(object):
    
    classes = {}
    
    # Find a better mapping here later
    typemap = { 
               'str': str(), 
               'int' : int(),
               'object' : GOsaDBObject()
               }

    
    def __init__(self, session):
        self.session = session
    
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
       
    def load(self, obj):
        cName = str(obj['type'])
        if cName in self.classes:
            cMeta = self.classes[cName]
            newObj = cMeta(gosa_object=obj)
            return newObj
        
        return obj
    
    def loadSchema(self, filename):
        
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

    def getClasses(self):
        return self.classes

    def _registerClass(self, name, props):

        # The class wasn't defined yet, create a new metaclass for it.
        if not name in globals():

            # Create the class 
            class klass(GOsaBaseObject):
                pass
                
            setattr(klass, '__name__', name)
            klass.session = self.session

            # populate the newly created class
            self.classes[name] = klass

        # Update metaclass properties
        klass = self.classes[name]
        if props:
            prop = {}
            properties = []
            for key in props:
                
                # Normalise xml-generated dict.
                # Look for a better solution later 
                propAttrs = key['property']
                prop = {}
                for pEntry in propAttrs:
                    for n in pEntry:
                        prop[n] = pEntry[n]
                
                # Add the property to the class
                properties.append(prop['name']) 
                setattr(klass, prop['name'], self.typemap[prop['type']])

            setattr(klass, '_db_properties', properties)

