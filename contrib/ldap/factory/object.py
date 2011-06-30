# -*- coding: utf-8 -*-
import os
import time
import datetime
from lxml import etree, objectify

# Map XML base types to python values
TYPE_MAP = {
        'Boolean': bool,
        'String': unicode,
        'Integer': int,
        'Timestamp': time.time,
        'Date': datetime.date,
        'Binary': None,
        'Dictionary': dict,
        'List': list,
        }


class GOsaObjectFactory(object):

    __xml_defs = {}
    __classes = {}

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
            self.__xml_defs[str(xml.Class['name'][0])] = xml

        except etree.XMLSyntaxError as e:
            print "Error:", e
            exit()

    #@Command()
    def getObjectInstance(self, name, *args, **kwargs):
        if not name in self.__classes:
            self.__classes[name] = self.__build_class(name)

        return self.__classes[name](*args, **kwargs)

    def __build_class(self, name):
        class klass(GOsaObject):

            def __init__(me, *args, **kwargs):
                GOsaObject.__init__(me, *args, **kwargs)

            def __setattr__(me, name, value):
                me._setattr_(name, value)

            def __getattr__(me, name):
                return me._getattr_(name)

            def __del__(me):
                me._del_()

        # Tweak name to the new target
        setattr(klass, '__name__', name)

        # What kind of properties do we have?
        classr = self.__xml_defs[name].Class
        props = {}

        # Add documentation if available
        if 'description' in classr:
            setattr(klass, '__doc__', str(classr['description']))

        try:
            for prop in classr['properties']['property']:
                syntax = str(prop['syntax'])
                props[str(prop['name'])] = {
                        'value': None,
                        'type': TYPE_MAP[syntax],
                        'syntax': syntax
                        }

        except KeyError:
            pass

        setattr(klass, '__properties', props)
        setattr(klass, '__methods', {})

        return klass


class GOsaObject(object):
    # This may contain some useful stuff later on

    def __init__(self):
        print "--> init"

    def _setattr_(self, name, value):
        props = getattr(self, '__properties')
        if name in props:

            if props[name]['type']:

                if issubclass(type(value), props[name]['type']):
                    props[name]['value'] = value

                else:
                    raise TypeError("cannot assign value '%s'(%s) to property '%s'(%s)" % (
                        value, type(value).__name__,
                        name, props[name]['syntax']))

            else:
                props[name]['value'] = value

        else:
            raise AttributeError("no such property '%s'" % name)

    def _getattr_(self, name):
        props = getattr(self, '__properties')
        methods = getattr(self, '__methods')

        if name in props:
            return props[name]['value']

        elif name in methods:
            return methods[name]['ref']

        else:
            raise AttributeError("no such property '%s'" % name)

    def _del_(self):
        print "--> cleanup"

    def commit(self):
        print "--> built in commit method"

    def delete(self):
        print "--> built in delete method"


def notify(message):
    """ Dummy method to be dispatched """
    print "Message:", message


# --------------------------------- Test -------------------------------------
f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person')
print "Object type:", type(p)

p.sn = u"Pollmeier"
print "sn:", p.sn
p.commit()
#p.notify("Hallo Karl-Gustav!")
