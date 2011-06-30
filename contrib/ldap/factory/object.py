# -*- coding: utf-8 -*-
import os
from lxml import etree, objectify


class GOsaObjectFactory(object):

    classes = {}

    def __init__(self, path):
        # Initialize parser
        schema_path = os.path.join(path, "object.xsd")
        schema_doc = open(schema_path).read()
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self.__parser = objectify.makeparser(schema=schema)

        # Load and parse schema
        self.load_schema(path)

    def load_schema(self, path):
        path = os.path.join(path, "objects")

        # Look on path and check for xml files
        for f in [n for n in os.listdir(path) if n.endswith(os.extsep + 'xml')]:
            self.__parse_schema(os.path.join(path, f))

    def __parse_schema(self, path):
        print "Loading %s..." % path

        # Load and validate objects
        try:
            xml = objectify.fromstring(open(path).read(), self.__parser)
            self.classes[str(xml.Class['name'][0])] = xml

        except etree.XMLSyntaxError as e:
            print "Error:", e
            exit()

    #@Command()
    def getObjectInstance(self, name, *args, **kwargs):
        print "Initializing object of type %s" % name

        class klass(GOsaObject):

            def __init__(me, *args, **kwargs):
                GOsaObject.__init__(me, *args, **kwargs)

            def __setattr__(me, name, value):
                me._setattr_(name, value)

            def __getattr__(me, name):
                return me._getattr_(name)

        # Tweak name to the new target
        setattr(klass, '__name__', name)

        # What kind of attributes do we have?
        classr = self.classes[name].Class
        props = {}

        try:
            for prop in classr['properties']['property']:
                print "Property %s (%s)" % (prop['name'], prop['type'])
                props[str(prop['name'])] = {
                        'value': None,
                        'type': str(prop['type'])}

        except KeyError:
            pass

        setattr(klass, '__properties', props)

        return klass(*args, **kwargs)



class GOsaObject(object):
    # This may contain some useful stuff later on

    def __init__(self):
        print "+++ superclass init"

    def _setattr_(self, name, value):
        props = getattr(self, '__properties')
        if name in props:
            props[name]['value'] = value
        else:
            raise AttributeError("no such property")

    def _getattr_(self, name):
        props = getattr(self, '__properties')
        if name in props:
            return props[name]['value']
        else:
            raise AttributeError("no such property")


# --------------------------------- Test -------------------------------------
f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person')

p.sn = "Pollmeier"
print p.sn
print type(p)
print p.__dict__
