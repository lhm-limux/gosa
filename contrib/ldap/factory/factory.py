# -*- coding: utf-8 -*-
import os
import time
import datetime
import re
from lxml import etree, objectify
from backend.registry import ObjectBackendRegistry, loadAttr

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

# Status
STATUS_OK = 0
STATUS_CHANGED = 1


class GOsaObjectFactory(object):

    __xml_defs = {}
    __classes = {}
    __var_regex = re.compile('^[a-z_][a-z0-9\-_]*$', re.IGNORECASE)

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
            self.__xml_defs[str(xml.Object['Name'][0])] = xml

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
        setattr(klass, '_backend', str(self.__xml_defs[name].Object.DefaultBackend))

        # What kind of properties do we have?
        classr = self.__xml_defs[name].Object
        props = {}
        methods = {}

        # Add documentation if available
        if 'description' in classr:
            setattr(klass, '__doc__', str(classr['description']))

        try:
            for prop in classr['Attributes']['Attribute']:

                # Do we have a input filter definition?
                in_f = None
                if len(getattr(prop, 'InFilter')):
#                    in_f = unicode(prop['InFilter']['Code'])
                    print objectify.dump(prop['InFilter'])
                    if len(getattr(prop['InFilter'], 'Backend')):
                        in_b = str(prop['InFilter']['Backend'])
                    else:
                        in_b = str(classr.DefaultBackend)

                # Do we have a input filter definition?
                in_f = None
                if len(getattr(prop, 'OutFilter')):
                    print objectify.dump(prop['OutFilter'])
                    if len(getattr(prop['OutFilter'], 'Backend')):
                        in_b = str(prop['OutFilter']['Backend'])
                    else:
                        in_b = str(classr.DefaultBackend)

                print "BREAK"
                exit()

                syntax = str(prop['Syntax'])
                props[str(prop['Name'])] = {
                        'value': None,
                        'orig': None,
                        'status': STATUS_OK,
                        'type': TYPE_MAP[syntax],
                        'syntax': syntax,
                        'in_filter': in_f,
                        'in_backend': in_b,
                        'multivalue': bool(prop['MultiValue'])
                        }

                #-----------------
                #validators....
                #-----------------

            for method in classr['Methods']['Method']:
                name = str(method['Name'])
                def funk(*args, **kwargs):
                    variables = {'title': args[0], 'message': args[1]}
                    self.__exec(unicode(str(method['Code']).strip()), variables)

                methods[name] = {
                        'ref': funk
                        }

        except KeyError:
            pass

        setattr(klass, '__properties', props)
        setattr(klass, '__methods', methods)

        return klass

    def __exec(self, code, args):
        for _key in args.keys():
            if self.__var_regex.match(_key):
                exec "%(key)s = args['%(key)s']" % {'key': _key}
            else:
                print u"\nNo! I don't like this key '%s'." % _key
                return

        exec code


class GOsaObject(object):
    # This may contain some useful stuff later on
    _reg = None
    _backend = None
    uuid = None

    def __init__(self, dn=None):
        if dn:
            print "--> init '%s'" % dn
            self._read(dn)

        else:
            print "--> empty init"

    def _read(self, dn):
        #TODO: look at all requrired backends and load the
        #      required data

        self._reg = ObjectBackendRegistry.getInstance()
        self.uuid = self._reg.dn2uuid(self._backend, dn)

        # Walk thru all properties and fill them accordingly
        props = getattr(self, '__properties')
        for key in props:
            obj = self
            dst = None

            if props[key]['in_filter']:
                #TODO: load all available filter in "filter.xxx" to
                #      make them available inside of the exec
                #TODO: load all available validators in "validator.xxx" to
                #      make them available inside of the exec
                print "Filter-processing is missing - break"
                exit()
            else:
                dst = loadAttr(obj, key)[0] if 'MultiValue' in props[key] and \
                    not props[key]['MultiValue'] else loadAttr(obj, key)

            props[key]['value'] = dst
            props[key]['old'] = dst

    def _setattr_(self, name, value):
        try:
            getattr(self, name)
            self.__dict__[name] = value
            return

        except:
            pass

        props = getattr(self, '__properties')
        if name in props:
            current = props[name]['value']

            # Run type check
            if props[name]['type'] and not issubclass(type(value), props[name]['type']):
                raise TypeError("cannot assign value '%s'(%s) to property '%s'(%s)" % (
                    value, type(value).__name__,
                    name, props[name]['syntax']))

            # Run validator
                #TODO: load all available filter in "filter.xxx" to
                #      make them available inside of the exec
                #TODO: load all available validators in "validator.xxx" to
                #      make them available inside of the exec
            props[name]['value'] = value

            # Update status if there's a change
            if current != props[name]['value'] and props[name]['status'] != STATUS_CHANGED:
                props[name]['status'] = STATUS_CHANGED
                props[name]['old'] = current

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

    def getAttrType(self, name):
        props = getattr(self, '__properties')
        if name in props:
            return props[name]['type']

        raise AttributeError("no such property '%s'" % name)

    def commit(self):
        print "--> built in commit method"
        # Schauen was sich so alles verändert hat, dann nach backend getrennt
        # in ein dict packen

    def delete(self):
        print "--> built in delete method"

    def revert(self):
        print "--> built in revert method"
        # Alle CHANGED attribute wieder zurück auf "old" setzen
