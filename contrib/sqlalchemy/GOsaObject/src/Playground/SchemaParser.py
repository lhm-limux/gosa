from GOsaDBObject import GOsaDBObject
import xml.etree.ElementTree as etree


# A mapping for xml-type to python-type conversion.
xmlToTypeMap = {
           'Boolean': bool(),
           'String': str(),
           'Integer': int(),
           'Object': GOsaDBObject(),
           'ObjectList': list()}


class GOsaBaseObject(object):
    """
    The base meta-class, which is used as mother class for all classes
    defined in the xml-schema.

    All attributes of this class will be mapped to an GOsaDBObject which
    allows to persist the information in a database.
    """

    # The GOsaDBObject - It is the sqlalchemy-orm object used to persists class
    # properties.
    gosa_object = None

    # A list of all property names this class can manage.
    _db_properties = ['type']

    def getObject(self):
        """
        Returns the SqlAlchemy ORM class - GOsaDBObject.
        Which can then be used directly, e.g to connect objects.
        """
        return self.gosa_object

    def __init__(self, uri=None, gosa_object=None):
        """
        Initializes the class and the gosa_object (GOsaDBObject).
        """
        if gosa_object:
            self.gosa_object = gosa_object
        else:
            self.gosa_object = GOsaDBObject(unicode(uri))
            self.gosa_object[u'type'] = unicode(self.__class__.__name__)

    def __getattribute__(self, name):
        """
        Getter method for class properties.

        If the requested attribute-name is part of the gosa_object, then
        return the value from it. If it is not, then return the attribute
        form ourselves directly.
        """

        # Return properties which are not part of the orm GOsaDBObject.
        db_props = object.__getattribute__(self, '_db_properties')
        if name not in db_props:
            return object.__getattribute__(self, name)

        else:

            # Return orm values.
            v = object.__getattribute__(self, name)

            # The value of the properties is a link to another orm GOsaDBObject.
            # Return it directly without type conversion.
            if isinstance(v, GOsaDBObject):
                return self.gosa_object[name]
            else:

                # Return the property value now and convert its type if
                # necessary.
                old_type = type(v)
                val = self.gosa_object[name]
                if val == None:
                    return old_type()
                else:
                    return old_type(self.gosa_object[name])

    def __setattr__(self, name, value):
        """
        Setter method for class properties.
        """

        # Do not save base class properties in the backend.
        db_props = object.__getattribute__(self, '_db_properties')
        if name in db_props:

            # Check if given value matches the requested types
            if (type(value) != type(getattr(self, name))) and not issubclass(type(value), GOsaDBObject):
                raise Exception("Invalid type given '%s', expected '%s'" % (type(value), type(getattr(self, name))))
            else:
                object.__setattr__(self, name, value)
                self.gosa_object[unicode(name)] = value
                return

        # Check if the given property exists
        if not hasattr(self, name):
            raise Exception("There is no such property '%s' for class '%s'." % (name, type(self)))
        else:
            object.__setattr__(self, name, value)


class SchemaLoader(object):
    """
    Loads schema files (xml) and constructs meta classes for each found class.

    """

    # A list of all constructed meta classes
    classes = {}

    def xml_to_dict(self, el):
        """
        Recursively creates a dictionary out of xml.
        """
        d = {}
        if el.text:
            d[el.tag] = el.text
        else:
            d[el.tag] = {}

        children = el.getchildren()

        if children:
            d[el.tag] = map(self.xml_to_dict, children)
        return d

    def __parse(self, filename):
        """
        Parses a given xml file (filename) into a useable dictionary.
        """
        tree = etree.parse(filename)
        return(self.xml_to_dict(tree.getroot()))

    def toObject(self, obj):
        """
        Converts a given GOsaDBObject (SqlAlchemy ORM class) into its xml
        defined ounterpart.
        """
        cName = str(obj['type'])
        if cName in self.classes:
            cMeta = self.classes[cName]
            newObj = cMeta(gosa_object=obj)
            return newObj

        return obj

    def loadSchema(self, filename):
        """
        Loads the given schema file and constructs meta classes for the class
        definition found.
        """
        schema = self.__parse(filename)
        for id in schema['Classes']:

            # Extract information out of the xml-dictionary
            className = properties = None
            extends = GOsaBaseObject
            for entry in id['Class']:
                if 'properties' in entry:
                    properties = entry['properties']

                if 'name' in entry:
                    className = entry['name']

                if 'extends' in entry:
                    eName = entry['extends']
                    if eName in self.classes:
                        extends = self.classes[eName]
                    else:
                        raise Exception("Cannot extends class '%s' from"
                                        " '%s'. The class '%s' wasn't "
                                        "defined yet!" % (
                                        className, eName, eName))

            # Construct the class now
            if className:
                self._registerClass(className, properties, extends)

    def getClasses(self):
        """
        Returns the list of constructed meta-classes
        """
        return self.classes

    def _registerClass(self, name, props, extends=GOsaBaseObject):
        """
        Constructs a new meta-class with given name, properites and father class.
        """

        # The class wasn't defined yet, create a new metaclass for it.
        if not name in globals():

            # Create the class
            class klass(extends):
                pass

            setattr(klass, '__name__', name)

            # populate the newly created class
            self.classes[name] = klass

        # Update metaclass properties
        klass = self.classes[name]
        if props:
            prop = {}
            properties = klass._db_properties
            for key in props:

                # Normalize xml-generated dict.
                # Look for a better solution later
                propAttrs = key['property']
                prop = {}
                for pEntry in propAttrs:
                    for n in pEntry:
                        prop[n] = pEntry[n]

                # Add the property to the class
                if prop['name'] not in properties:
                    properties.append(prop['name'])

                setattr(klass, prop['name'], xmlToTypeMap[prop['type']])

            # Update property list in meta class
            klass._db_properties = properties
