from GOsaObject import GOsaObject
import xml.etree.ElementTree as etree


class GOsaBaseObject(object):

    session = None
    gosa_object = None

    def __init__(self, uri = None, gosa_object=None):
        
        if gosa_object:
            self.gosa_object = gosa_object
        else:
            self.gosa_object = GOsaObject(unicode(uri))
            self.gosa_object['__class_type'] = self.__class__.__name__

    def add(self):
        self.session.add(self.gosa_object)

    def getSession(self):
        return(self.session)
    
    def __getattribute__(self, name):

        if name in ['gosa_object', 'session', 'add', 'getSession']:
            return object.__getattribute__(self, name)
        
        if name in self.gosa_object:
            v = object.__getattribute__(self, name)
            if isinstance(v, GOsaObject):
                return self.gosa_object[name]
            else:
                old_type = type(v)
                return old_type(self.gosa_object[name])
           
        raise Exception("There is no such property '%s' for class '%s'." % (name, type(self)))

    def __setattr__(self, name, value):
        
        name = unicode(name)
        
        # Do not save base class properties in the backend.
        #if name in dir(GOsaBaseObject):
        if name in ['gosa_object', 'session', 'add','getSession']:
            object.__setattr__(self, name, value)
            return
        
        print name
        
        # Check if the given property was defined in the xml schema
        if not hasattr(self, name):
            raise Exception("There is no such property '%s' for class '%s'." % (name, type(self)))
            return

        # Check if given value matches the requested types 
        if (type(value) != type(getattr(self, name))) and not isinstance(value, GOsaObject):
            raise Exception("Invalid type given '%s', expected '%s'" % (type(value), type(getattr(self, name))))
        else:
            object.__setattr__(self, name, value)
            self.gosa_object[name] = value


class SchemaLoader(object):
    
    classes = {}
    
    # Find a better mapping here later
    typemap = {'str': str(), 'int' : int()}

    
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
        cName = str(obj['__class_type'])
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
            print "Created class: %s" % name

        # Update metaclass properties
        klass = self.classes[name]
        if props:
            for key in props:
                
                # Normalise xml-generated dict.
                # Look for a better solution later 
                propAttrs = key['property']
                prop = {}
                for pEntry in propAttrs:
                    for n in pEntry:
                        prop[n] = pEntry[n]
                

                
                # Add the property to the class
                setattr(klass, prop['name'], self.typemap[prop['type']])
        

        
