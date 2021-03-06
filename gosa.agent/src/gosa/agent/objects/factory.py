# -*- coding: utf-8 -*-
"""

GOsa Object Factory
===================

Short description
^^^^^^^^^^^^^^^^^

The object factory provides access to backend-data in an object
oriented way. You can create, read, update and delete objects easily.

What object-types are avaialable is configured using XML files, these files
are located here: ``./gosa.common/src/gosa/common/data/objects/``.

Each XML file can contain multiple object definitions, with object related
information, like attributes, methods, how to store and read
objects.

(For a detailed documentation of the of XML files, please have a look at the
./doc directory)

A python meta-class will be created for each object-definition.
Those meta-classes will then be used to instantiate a new python object,
which will then provide the defined attributes, methods, aso.

Here are some examples on how to instatiate on new object:

>>> from gosa.agent.objects import GOsaObjectFactory
>>> person = f.getObject('Person', "410ad9f0-c4c0-11e0-962b-0800200c9a66")
>>> print person->sn
>>> person->sn = "Surname"
>>> person->commit()

"""
import pkg_resources
import os
import time
import copy
import datetime
import re
import logging
import zope.event
from zope.interface import Interface, implements
from lxml import etree, objectify
from gosa.common import Environment
from gosa.agent.objects.filter import get_filter
from gosa.agent.objects.backend.registry import ObjectBackendRegistry
from gosa.agent.objects.comparator import get_comparator
from gosa.agent.objects.operator import get_operator
from logging import getLogger

# Map XML base types to python values
TYPE_MAP = {
        'Boolean': bool,
        'String': str,
        'UnicodeString': unicode,
        'Integer': int,
        'Timestamp': datetime.datetime,
        'Date': datetime.date,
        'Binary': None
        }

# Status
STATUS_OK = 0
STATUS_CHANGED = 1


class FactoryException(Exception):
    pass

class GOsaObjectFactory(object):
    """
    This class reads GOsa-object defintions and generates python-meta classes
    for each object, which can then be instantiated using
    :meth:`gosa.agent.objects.factory.GOsaObjectFactory.getObject`.
    """
    __xml_defs = {}
    __classes = {}
    __var_regex = re.compile('^[a-z_][a-z0-9\-_]*$', re.IGNORECASE)

    def __init__(self):
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)

        # Initialize parser
        #pylint: disable=E1101
        schema_path = pkg_resources.resource_filename('gosa.agent', 'data/objects/object.xsd')
        schema_doc = open(schema_path).read()
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self.__parser = objectify.makeparser(schema=schema)

        self.log.info("object factory initialized")

        # Load and parse schema
        self.loadSchema()

#-TODO-needs-re-work-------------------------------------------------------------------------------

    #@Command()
    def identifyObject(self, dn):
        obr = ObjectBackendRegistry.getInstance()
        id_base = None
        id_extend = []

        # First, find all base objects
        # -> for every base object -> ask the primary backend to identify [true/false]
        for name, obj in self.__xml_defs.items():
            t_obj = obj.Object
            is_base = bool(t_obj.BaseObject)
            backend = str(t_obj.Backend)
            for bp in t_obj.BackendParameters.Backend:
                if str(bp) == backend:
                    attrs = bp.attrib
                    break

            be = ObjectBackendRegistry.getBackend(backend)
            if be.identify(dn, attrs):
                if is_base:
                    id_base = name
                else:
                    id_extend.append(name)

        if id_base:
            return (id_base, id_extend)

        return None

    #@Command()
    def getObject(self, name, *args, **kwargs):
        """
        Returns a GOsa-object instance.

        e.g.:

        >>> person = f.getObject('Person', "410ad9f0-c4c0-11e0-962b-0800200c9a66")

        """
        self.log.debug("object of type '%s' requested %s" % (name, args))
        if not name in self.__classes:
            self.__classes[name] = self.__build_class(name)

        return self.__classes[name](*args, **kwargs)

    #@Command()
    def createObject(self, name, *args, **kwargs):
        #TODO
        pass

    #@Command()
    def removeObject(self, name, uuid, recursive=False):
        #TODO
        pass

    #@Command()
    def getObjectExtensions(self, name, *args, **kwargs):
        #TODO
        pass

    #@Command()
    def getObjectExtension(self, name, *args, **kwargs):
        #TODO
        pass

    #@Command()
    def createObjectExtension(self, name, *args, **kwargs):
        #TODO
        pass

    #@Command()
    def removeObjectExtension(self, name, uuid):
        #TODO
        pass

#----------------------------------------------------------------------------------------

    @staticmethod
    def createNewProperty(backend, atype, dependsOn=[], backend_type=None, validator=[], in_f=[], out_f=[],
            unique=False, mandatory=False, readonly=False, multivalue=False, foreign=False, status=STATUS_OK,
            value=[], skip_save=False):

        if not backend_type:
            backend_type = atype

        ret = {
                'value': value,
                'status': status,
                'dependsOn': dependsOn,
                'type': atype,
                'backend_type': backend_type,
                'validator': validator,
                'out_filter': out_f,
                'in_filter': in_f,
                'backend': backend,
                'orig_value': value,
                'foreign': foreign,
                'unique': unique,
                'mandatory': mandatory,
                'readonly': readonly,
                'skip_save': skip_save,
                'multivalue': multivalue}
        return ret


    def loadSchema(self):
        """
        This method reads all gosa-object defintion files and then calls
        :meth:`gosa.agent.objects.factory.GOsaObjectFactory.getObject`
        to initiate the parsing into meta-classes for each file.

        These meta-classes are used for object instantiation later.

        """
        #pylint: disable=E1101
        path = pkg_resources.resource_filename('gosa.agent', 'data/objects')

        # Include built in schema
        for f in [n for n in os.listdir(path) if n.endswith(os.extsep + 'xml')]:
            self.__parse_schema(os.path.join(path, f))

        # Include additional schema configuration
        path = os.path.join(self.env.config.getBaseDir(), 'schema')
        if os.path.isdir(path):
            for f in [n for n in os.listdir(path) if n.endswith(os.extsep + 'xml')]:
                self.__parse_schema(os.path.join(path, f))

    def __parse_schema(self, path):
        """
        Parses a schema file using the
        :meth:`gosa.agent.objects.factory.GOsaObjectFactory.__parser`
        method.
        """
        try:
            xml = objectify.fromstring(open(path).read(), self.__parser)
            self.__xml_defs[str(xml.Object['Name'][0])] = xml
            self.log.info("loaded schema file for '%s' (%s)" % (str(xml.Object['Name'][0]),path))

        except etree.XMLSyntaxError as e:
            raise FactoryException("Error loading object-schema file: %s, %s" % (path, e))

    def __build_class(self, name):
        """
        This method builds a meta-class for each object defintion read from the
        xml defintion files.

        It uses a base-meta-class which will be extended by the define
        attributes and mehtods of the object.

        The final meta-class will be stored and can then be requested using:
        :meth:`gosa.agent.objects.factory.GOsaObjectFactory.getObject`
        """

        self.log.debug("building meta-class for object-type '%s'" % (name,))

        class klass(GOsaObject):

            #pylint: disable=E0213
            def __init__(me, *args, **kwargs):
                GOsaObject.__init__(me, *args, **kwargs)

            #pylint: disable=E0213
            def __setattr__(me, name, value):
                me._setattr_(name, value)

            #pylint: disable=E0213
            def __getattr__(me, name):
                return me._getattr_(name)

            #pylint: disable=E0213
            def __delattr__(me, name):
                me._delattr_(name)

            #pylint: disable=E0213
            def __del__(me):
                me._del_()

        # Collect Backend attributes per Backend
        back_attrs = {}
        classr = self.__xml_defs[name].Object
        if "BackendParameters" in classr.__dict__:
            for entry in classr["BackendParameters"]:
                back_attrs[str(entry.Backend)] = entry.Backend.attrib

        # Collect extends lists. A list of objects that we can extend.
        extends = []
        if "Extends" in classr.__dict__:
            for entry in classr["Extends"]:
                extends.append(str(entry.Value))

        # Load object properties like: is base object and allowed container elements
        base_object = bool(classr['BaseObject']) if "BaseObject" in classr.__dict__ else False
        container = []
        if "Container" in classr.__dict__:
            for entry in classr["Container"]:
                container.append(str(entry.Type))

        # Tweak name to the new target
        setattr(klass, '__name__', name)
        setattr(klass, '_backend', str(classr.Backend))
        setattr(klass, '_backendAttrs', back_attrs)
        setattr(klass, '_extends', extends)
        setattr(klass, '_base_object', base_object)
        setattr(klass, '_container_for', container)

        # Prepare property and method list.
        props = {}
        methods = {}

        # Add documentation if available
        if 'Description' in classr.__dict__:
            setattr(klass, '_description', str(classr['Description']))

        # Load the backend and its attributes
        defaultBackend = str(classr.Backend)

        # Append attributes
        for prop in classr['Attributes']['Attribute']:

            self.log.debug("adding property: '%s'" % (str(prop['Name']),))

            # Read backend definition per property (if it exists)
            backend = defaultBackend
            if "Backend" in prop.__dict__:
                backend = str(prop.Backend)

            # Do we have an output filter definition?
            out_f = []
            if "OutFilter" in prop.__dict__:
                for entry in  prop['OutFilter'].iterchildren():
                    self.log.debug(" appending out-filter")
                    of = self.__handleFilterChain(entry)
                    out_f.append(of)

            # Do we have a input filter definition?
            in_f =  []
            if "InFilter" in prop.__dict__:
                for entry in  prop['InFilter'].iterchildren():
                    self.log.debug(" appending in-filter")
                    in_f.append(self.__handleFilterChain(entry))

            # Read and build up validators
            validator =  None
            if "Validators" in prop.__dict__:
                self.log.debug(" appending property validator")
                validator = self.__build_filter(prop['Validators'])

            # Read the properties syntax
            syntax = str(prop['Type'])
            backend_syntax = syntax
            if "BackendType" in prop.__dict__:
                backend_syntax = str(prop['BackendType'])

            # check for multivalue, mandatory and unique definition
            multivalue = bool(prop['MultiValue']) if "MultiValue" in prop.__dict__ else False
            unique = bool(prop['Unique']) if "Unique" in prop.__dict__ else False
            mandatory = bool(prop['Mandatory']) if "Mandatory" in prop.__dict__ else False
            readonly = bool(prop['Readonly']) if "Readonly" in prop.__dict__ else False
            foreign = bool(prop['Foreign']) if "Foreign" in prop.__dict__ else False

            # Check for property dependencies
            dependsOn = []
            if "DependsOn" in prop.__dict__:
                for d in prop.__dict__['DependsOn'].iterchildren():
                    dependsOn.append(str(d))

            # Create a new property with the given information
            props[str(prop['Name'])] =  new_prop = GOsaObjectFactory.createNewProperty(backend, syntax,
                    dependsOn=dependsOn, backend_type=backend_syntax, validator=validator, in_f=in_f,
                    out_f=out_f, unique=unique, mandatory=mandatory, readonly=readonly,
                    multivalue=multivalue, foreign=foreign, status=STATUS_OK, value=None)

        # Build up a list of callable methods
        if 'Methods' in classr.__dict__:
            for method in classr['Methods']['Method']:

                # Extract method information out of the xml tag
                methodName = str(method['Name'])
                command = str(method['Command'])

                # Get the list of method parameters
                mParams = []
                if 'MethodParameters' in method.__dict__:

                    # Todo: Check type of the property and handle the
                    # default value.

                    for param in method['MethodParameters']['MethodParameter']:
                        pName = str(param['Name'])
                        pType = str(param['Type'])
                        pRequired = bool(param['Required']) if 'Required' in param.__dict__ else False
                        pDefault = str(param['Default']) if 'Default' in param.__dict__ else None
                        mParams.append( (pName, pType, pRequired, pDefault), )

                # Get the list of command parameters
                cParams = []
                if 'CommandParameters' in method.__dict__:
                    for param in method['CommandParameters']['CommandParameter']:
                        cParams.append(str(param['Value']))

                # Now add the method to the object
                def funk(*args, **kwargs):

                    # Convert all given parameters into named arguments
                    # The eases up things a lot.
                    cnt = 0
                    arguments = {}
                    for mParam in mParams:
                        mName, mType, mRequired, mDefault = mParam
                        if mName in kwargs:
                            arguments[mName] = kwargs[mName]
                        elif cnt < len(args):
                            arguments[mName] = args[cnt]
                        elif mDefault:
                            arguments[mName] = TYPE_MAP[mType](mDefault)
                        else:
                            raise FactoryException("Missing parameter '%s'!" % mName)

                        # Ensure that the correct parameter type was given.
                        if TYPE_MAP[mType] != type(arguments[mName]):
                            raise FactoryException("Invalid parameter type given for '%s', expected "
                                "'%s' but received '%s'!" % (mName,
                                    TYPE_MAP[mType],type(arguments[mName])))

                        cnt = cnt + 1

                    # Build the command-parameter list.
                    # Collect all property values of this GOsa-object to be able to fill in
                    # placeholders in command-parameters later.
                    propList = {}
                    for key in props:
                        propList[key] = props[key]['value']

                    # Add method-parameters passed to this method.
                    for entry in arguments:
                        propList[entry] = arguments[entry]

                    # Fill in the placeholders of the command-parameters now.
                    parameterList = []
                    for value in cParams:
                        try:
                            value = value % propList
                        except:
                            raise FactoryException("Cannot call method '%s', error while filling "
                                " in placeholders! Error processing: %s!" %
                                (methodName, value))

                        parameterList.append(value)

                    #TODO: Execute real-stuff later
                    print "Calling class method:", parameterList, command

                # Append the method to the list of registered methods for this
                # object
                self.log.debug("adding method: '%s'" % (methodName, ))
                methods[methodName] = {'ref': funk}

        # Set properties and methods for this object.
        setattr(klass, '__properties', props)
        setattr(klass, '__methods', methods)
        return klass

    def __build_filter(self, element, out=None):
        """
        Attributes of GOsa objects can be filtered using in- and out-filters.
        These filters can manipulate the raw-values while they are read form
        the backend or they can manipulate values that have to be written to
        the backend.

        This method converts the read XML filter-elements of the defintion into
        a process lists. This list can then be easily executed line by line for
        each property, using the method:

        :meth:`gosa.agent.objects.factory.GOsaObject.__processFilter`

        """

        # Parse each <FilterChain>, <Condition>, <ConditionChain>
        out = {}
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}FilterChain":
                out = self.__handleFilterChain(el, out)
            elif  el.tag == "{http://www.gonicus.de/Objects}Condition":
                out = self.__handleCondition(el, out)
            elif  el.tag == "{http://www.gonicus.de/Objects}ConditionOperator":
                out = self.__handleConditionOperator(el, out)

        return out

    def __handleFilterChain(self, element, out=None):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'FilterChain' element is handled here.

        Occurrence: OutFilter->FilterChain
        """
        if not out:
            out = {}

        # FilterChains can contain muliple "FilterEntry" tags.
        # But at least one.
        # Here we forward these elements to their handler.
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}FilterEntry":
                out = self.__handleFilterEntry(el, out)
        return out

    def __handleFilterEntry(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'FilterEntry' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry
        """

        # FilterEntries contain a "Filter" OR a "Choice" tag.
        # Here we forward the elements to their handler.
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}Filter":
                out = self.__handleFilter(el, out)
            elif el.tag == "{http://www.gonicus.de/Objects}Choice":
                out = self.__handleChoice(el, out)
        return out

    def __handleFilter(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'Filter' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Filter
        """

        # Get the <Name> and the <Param> element values to be able
        # to create a process list entry.
        name = str(element.__dict__['Name'])
        params = []
        for entry in element.iterchildren():
            if entry.tag == "{http://www.gonicus.de/Objects}Param":
                params.append(entry.text)

        # Attach the collected filter and parameter value to the process list.
        cnt = len(out) + 1
        out[cnt] = {'filter': get_filter(name)(self), 'params': params}
        return out

    def __handleChoice(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'Choice' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice
        """

        # We just forward <When> tags to their handler.
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}When":
                out = self.__handleWhen(el, out)
        return(out)

    def __handleWhen(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'When' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice->When
        """

        # (<When> tags contain a <ConditionChain>, a <FilterChain> tag and
        # an optional <Else> tag.
        #  The <FilterChain> is only executed when the <ConditionChain> matches
        #  the given values.)

        # Forward the tags to their correct handler.
        filterChain = {}
        elseChain = {}
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}ConditionChain":
                out = self.__handleConditionChain(el, out)
            if el.tag == "{http://www.gonicus.de/Objects}FilterChain":
                filterChain = self.__handleFilterChain(el, filterChain)
            elif el.tag == "{http://www.gonicus.de/Objects}Else":
                elseChain = self.__handleElse(el, elseChain)

        # Collect jump points
        cnt = len(out)
        match = cnt + 2
        endMatch = match + len(filterChain)
        noMatch = endMatch + 1
        endNoMatch = noMatch + len(elseChain)

        # Add jump point for this condition
        cnt = len(out)
        out[cnt + 1] = {'jump': 'conditional', 'onTrue': match, 'onFalse': noMatch}

        # Add the <FilterChain> process.
        cnt = len(out)
        for entry in filterChain:
            cnt = cnt + 1
            out[cnt] = filterChain[entry]

        # Add jump point to jump over the else chain
        cnt = len(out)
        out[cnt + 1] = {'jump': 'non-conditional', 'to': endNoMatch}

        # Add the <Else> process.
        cnt = len(out)
        for entry in elseChain:
            cnt = cnt + 1
            out[cnt] = elseChain[entry]

        return(out)

    def __handleElse(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'Else' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice->Else
        """

        # Handle <FilterChain> elements of this else tree.
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}FilterChain":
                out = self.__handleFilterChain(el, out)

        return out

    def __handleConditionChain(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'ConditionChain' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice->When->ConditionChain
        """

        # Forward <Condition> tags to their handler.
        for el in element.iterchildren():
            if el.tag == "{http://www.gonicus.de/Objects}Condition":
                out = self.__handleCondition(el, out)
            elif el.tag == "{http://www.gonicus.de/Objects}ConditionOperator":
                out = self.__handleConditionOperator(el, out)

        return out

    def __handleConditionOperator(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'ConditionOperator' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice->When->ConditionChain->ConditionOperator
        """

        # Forward <Left and <RightConditionChains> to the ConditionChain handler.
        out = self.__handleConditionChain(element.__dict__['LeftConditionChain'], out)
        out = self.__handleConditionChain(element.__dict__['RightConditionChain'], out)

        # Append operator
        cnt = len(out)
        if element.__dict__['Operator'] == "or":
            out[cnt + 1] = {'operator': get_operator('Or')(self)}
        else:
            out[cnt + 1] = {'operator': get_operator('And')(self)}

        return out

    def __handleCondition(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'Condition' element is handled here.

        Occurrence: OutFilter->FilterChain->FilterEntry->Choice->When->ConditionChain->Condition
        """

        # Get the condition name and the parameters to use.
        # The name of the condition specifies which ElementComparator
        # we schould use.
        name = str(element.__dict__['Name'])
        params = []
        for entry in element.iterchildren():
            if entry.tag == "{http://www.gonicus.de/Objects}Param":
                params.append(entry.text)

        # Append the condition to the process list.
        cnt = len(out) + 1
        out[cnt] = {'condition': get_comparator(name)(self), 'params': params}
        return(out)


class GOsaObject(object):
    """
    This class is the base class for all GOsa-objects.

    It contains getter and setter methods for the object
    attributes and it is able to initialize itself by reading data from
    backends.

    It also contains the ability to execute the in- and out-filters for the
    object properties.

    All meta-classes for GOsa-objects, created by the XML defintions, will inherit this class.

    """
    _reg = None
    _backend = None
    _mode = False
    _propsByBackend = {}
    uuid = None
    dn = None
    log = None

    def __init__(self, dn=None, mode="update"):

        # Instantiate Backend-Registry
        self._reg = ObjectBackendRegistry.getInstance()
        self. dn = dn
        self.log = getLogger(__name__)
        self.log.debug("new object instantiated '%s'" % (type(self).__name__))
        self.log.debug("object dn '%s'" % (dn))

        # Group attributes by Backend
        propsByBackend = {}
        props = getattr(self, '__properties')
        for key in props:

            # Initialize an empty array for each backend
            if props[key]['backend'] not in propsByBackend:
                propsByBackend[props[key]['backend']] = []

            # Append property
            propsByBackend[props[key]['backend']].append(key)

        self._propsByBackend = propsByBackend
        self._mode = mode

        # Initialize object using a DN
        if dn and mode != "create":
            self._read(dn)

    def listProperties(self):
        props = getattr(self, '__properties')
        return(props.keys())

    def _read(self, dn):
        """
        This method tries to initialize a GOsa-object instance by reading data
        from the defined backend.

        Attributes will be grouped by their backend to ensure that only one
        request per backend will be performed.

        """
        props = getattr(self, '__properties')

        # Instantiate Backend-Registry
        self.uuid = self._reg.dn2uuid(self._backend, dn)

        # Load attributes for each backend.
        # And then assign the values to the properties.
        obj = self
        self.log.debug("object uuid: %s" % (self.uuid))
        for backend in self._propsByBackend:

            try:
                # Create a dictionary with all attributes we want to fetch
                # {attribute_name: type, name: type}
                info = dict([(k, props[k]['backend_type']) for k in self._propsByBackend[backend]])
                self.log.debug("loading attributes for backend '%s': %s" % (backend, str(info)))
                be = ObjectBackendRegistry.getBackend(backend)
                attrs = be.load(self.uuid, info)

            except ValueError as e:
                #raise FactoryException("Error reading properties for backend '%s'!" % (backend,))
                import traceback
                traceback.print_exc()
                exit()

            # Assign fetched value to the properties.
            for key in self._propsByBackend[backend]:

                if key not in attrs:
                    #raise FactoryException("Value for '%s' could not be read, it wasn't returned by the backend!" % (key,))
                    self.log.debug("attribute '%s' was not returned by load!" % (key))
                    continue

                # Keep original values, they may be overwritten in the in-filters.
                props[key]['orig_value'] = props[key]['value'] = attrs[key]
                self.log.debug("%s: %s" % (key, props[key]['value']))

            # Once we've loaded all properties from the backend, execute the
            # in-filters.
            for key in self._propsByBackend[backend]:

                # Skip loading in-filters for None values
                if props[key]['value'] == None:
                    props[key]['orig_value'] = props[key]['value'] = []
                    continue

                # Execute defined in-filters.
                if len(props[key]['in_filter']):
                    self.log.debug("found %s in-filter(s)  for attribute '%s'" % (str(len(props[key]['in_filter'])),key))
                    value = props[key]['value']

                    # Execute each in-filter
                    for in_f in props[key]['in_filter']:
                        valDict = {key: copy.deepcopy(props[key])}
                        self.__processFilter(in_f, key, valDict)

                        # Assign filter results
                        for new_key in valDict:
                            self.log.debug("in-filter returned %s: '%s'" % (new_key, valDict[new_key]['value']))
                            props[new_key] =  valDict[new_key]

        # Convert the received type into the target type if not done already
        for key in props:
            if props[key]['type'] == 'Object':
                continue

            if props[key]['value'] and \
                    TYPE_MAP[props[key]['type']] and \
                    not all(map(lambda x: type(x) == TYPE_MAP[props[key]['type']], props[key]['value'])):
                props[key]['value'] = map(lambda x: TYPE_MAP[props[key]['type']](x), props[key]['value'])
                self.log.debug("converted '%s' to type '%s'!" % (key,props[key]['type']))

            # Keep the initial value
            props[key]['old'] = props[key]['value']

    def _delattr_(self, name):
        """
        Deleter method for properties.
        """
        props = getattr(self, '__properties')
        if name in props:

            # Do not allow to write to read-only attributes.
            if props[name]['readonly']:
                raise AttributeError("Cannot write to readonly attribute '%s'" % name)

            props[name]['value'] = []
        else:
            raise AttributeError("no such property '%s'" % name)

    def _setattr_(self, name, value):
        """
        This is the setter method for GOsa-object attributes.
        Each given attribute value is validated with the given set of
        validators.
        """

        # Store non property values
        try:
            object.__getattribute__(self, name)
            self.__dict__[name] = value
            return
        except AttributeError:
            pass

        # A none value was passed to clear the value
        if value == None:
            self._delattr_(name)
            return

        # Try to save as property value
        props = getattr(self, '__properties')
        if name in props:

            # Do not allow to write to read-only attributes.
            if props[name]['readonly']:
                raise AttributeError("Cannot write to readonly attribute '%s'" % name)

            current = copy.deepcopy(props[name]['value'])

            # Run type check (Multi-value and single-value separately)
            if props[name]['multivalue']:

                # We require lists for multi-value objects
                if type(value) != list:
                    raise TypeError("Cannot assign multi-value '%s' to property '%s'. A list is required for multi-values!" % (
                        value, name))

                # Check each list value for the required type
                failed = 0
                for entry in value:
                    if TYPE_MAP[props[name]['type']] and not issubclass(type(value[failed]), TYPE_MAP[props[name]['type']]):
                        raise TypeError("Cannot assign multi-value '%s' to property '%s' which expects %s. Item %s is of invalid type %s!" % (
                            value, name, props[name]['type'], failed, type(value[failed])))
                    failed += 1
            else:

                # Check single-values here.
                if TYPE_MAP[props[name]['type']] and not issubclass(type(value), TYPE_MAP[props[name]['type']]):
                    raise TypeError("cannot assign value '%s'(%s) to property '%s'(%s)" % (
                        value, type(value).__name__,
                        name, props[name]['type']))

            # Set the new value
            if props[name]['multivalue']:
                new_value = value
            else:
                new_value = [value]

            # Validate value
            if props[name]['validator']:
                res, error = self.__processValidator(props[name]['validator'], name, new_value)
                if not res:
                    if len(error):
                        raise ValueError("Property (%s) validation failed! Last error was: %s" % (name, error[0]))
                    else:
                        raise ValueError("Property (%s) validation failed without error!" % (name,))

            # Ensure that unique values stay unique. Let the backend test this.
            #if props[name]['unique']:
            #    backendI = ObjectBackendRegistry.getBackend(props[name]['backend'])
            #    if not backendI.is_uniq(name, new_value):
            #        raise FactoryException("The property value '%s' for property %s is not unique!" % (value, name))

            # Assign the properties new value.
            props[name]['value'] = new_value
            self.log.debug("updated property value of [%s|%s] %s:%s" % (type(self).__name__, self.uuid, name, new_value))

            # Update status if there's a change
            if current != props[name]['value'] and props[name]['status'] != STATUS_CHANGED:
                props[name]['status'] = STATUS_CHANGED
                props[name]['old'] = current

        else:
            raise AttributeError("no such property '%s'" % name)

    def _getattr_(self, name):
        """
        The getter method GOsa-object attributes.

        (It differentiates between GOsa-object attributes and class-members)
        """
        props = getattr(self, '__properties')
        methods = getattr(self, '__methods')

        # If the requested property exists in the object-attributes, then return it.
        if name in props:

            # We can have single and multivalues, return the correct type here.
            if props[name]['multivalue']:
                return props[name]['value']
            else:
                if len(props[name]['value']):
                    return props[name]['value'][0]
                else:
                    return None

        # The requested property-name seems to be a method, return the method reference.
        elif name in methods:
            return methods[name]['ref']

        else:
            raise AttributeError("no such property '%s'" % name)

    def getAttrType(self, name):
        """
        Return the type of a given GOsa-object attribute.
        """

        props = getattr(self, '__properties')
        if name in props:
            return props[name]['type']

        raise AttributeError("no such property '%s'" % name)

    def commit(self):
        """
        Commits changes of an GOsa-object to the corresponding backends.
        """
        props = getattr(self, '__properties')

        # Check if _mode matches with the current object type
        if self._base_object and not self._mode in ['create', 'remove', 'update']:
            raise FactoryException("mode '%s' not available for base objects" % self._mode)
        if not self._base_object and self._mode in ['create', 'remove']:
            raise FactoryException("mode '%s' only available for base objects" % self._mode)

        self.log.debug("saving object modifications for [%s|%s]" % (type(self).__name__, self.uuid))

        # Check if all required attributes are set.
        #for key in props:
        #    if props[key]['mandatory'] and not props[key]['value']:
        #        raise FactoryException("The required property '%s' is not set!" % (key,))

        # Collect values by store and process the property filters
        toStore = {}
        for key in props:

            # Adapt status from dependent properties.
            for propname in props[key]['dependsOn']:
                props[key]['status'] |= props[propname]['status'] & STATUS_CHANGED

            # Do not save untouched values
            if not props[key]['status'] & STATUS_CHANGED:
                continue

            # Get the new value for the property and execute the out-filter
            value = props[key]['value']
            new_key = key

            self.log.debug("changed: %s" % (key,))

            # Process each and every out-filter with a clean set of input values,
            #  to avoid that return-values overwrite themselves.
            if len(props[key]['out_filter']):

                self.log.debug(" found %s out-filter for %s" % (str(len(props[key]['out_filter'])), key,))
                for out_f in props[key]['out_filter']:
                    valDict = copy.deepcopy(props)
                    valDict = self.__processFilter(out_f, key, valDict)

                    # Collect properties by backend
                    for prop_key in valDict:

                        # Do not save untouched values
                        if not valDict[prop_key]['status'] & STATUS_CHANGED:
                            continue

                        # do not save properties that are marked with 'skip_save'
                        #self.log.debug(" outfilter returned %s:(%s) %s" % (prop_key, valDict[prop_key]['type'], valDict[prop_key]['value']))
                        if valDict[prop_key]['skip_save']:
                            continue

                        # Create backend entry in the target list.
                        be = valDict[prop_key]['backend']
                        if not be in toStore:
                            toStore[be] = {}

                        # Append entry to be sored.
                        toStore[be][prop_key] = {'foreign': props[key]['foreign'],
                                                 'orig': props[key]['orig_value'],
                                                 'value': valDict[prop_key]['value'],
                                                 'type': valDict[prop_key]['backend_type']}
            else:

                # do not save properties that are marked with 'skip_save'
                if props[key]['skip_save']:
                    continue

                # Collect properties by backend
                be = props[key]['backend']
                if not be in toStore:
                    toStore[be] = {}

                toStore[be][key] = {'foreign': props[key]['foreign'],
                                    'orig': props[key]['orig_value'],
                                    'value': props[key]['value'],
                                    'type': props[key]['backend_type']}

        # Handle by backend
        p_backend = getattr(self, '_backend')
        obj = self
        zope.event.notify(ObjectChanged("pre %s" % self._mode, obj))

        # First, take care about the primary backend...
        if p_backend in toStore:
            be = ObjectBackendRegistry.getBackend(p_backend)
            if self._mode == "create":
                be.create(self.dn, toStore[p_backend], self._backendAttrs[p_backend])
            elif self._mode == "extend":
                be.extend(self.uuid, toStore[p_backend],
                        self._backendAttrs[p_backend],
                        self.getForeignProperties())
            else:
                be.update(self.uuid, toStore[p_backend])

        # ... then walk thru the remaining ones
        for backend, data in toStore.items():

            # Skip primary backend - already done
            if backend == p_backend:
                continue

            be = ObjectBackendRegistry.getBackend(backend)

            if self._mode == "create":
                be.create(self.dn, data, self._backendAttrs[backend])
            elif self._mode == "extend":
                be.extend(self.uuid, data, self._backendAttrs[backend])
            else:
                be.update(self.uuid, data)

        zope.event.notify(ObjectChanged("post %s" % self._mode, obj))

    def revert(self):
        """
        Reverts all changes made to this object since it was loaded.
        """
        props = getattr(self, '__properties')
        for key in props:
            props[key]['value'] = props[key]['old']

        self.log.debug("reverted object modifications for [%s|%s]" % (type(self).__name__, self.uuid))

    def getExclusiveProperties(self):
        props = getattr(self, '__properties')
        return [x for x, y in props.items() if not y['foreign']]

    def getForeignProperties(self):
        props = getattr(self, '__properties')
        return [x for x, y in props.items() if y['foreign']]

    def __processValidator(self, fltr, key, value):
        """
        This method processes a given process-list (fltr) for a given property (prop).
        And return TRUE if the value matches the validator set and FALSE if
        not.
        """

        # This is our process-line pointer it points to the process-list line
        #  we're executing at the moment
        lptr = 0

        # Our filter result stack
        stack = list()
        self.log.debug(" validator started (%s)" % (key))
        self.log.debug("  value: %s" % (value, ))

        # Process the list till we reach the end..
        lasterrmsg = ""
        errormsgs = []
        while (lptr + 1) in fltr:

            # Get the current line and increase the process list pointer.
            lptr = lptr + 1
            curline = fltr[lptr]

            # A condition matches for something and returns a boolean value.
            # We'll put this value on the stack for later use.
            if 'condition' in curline:

                # Build up argument list
                args = [key, value] + curline['params']

                # Process condition and keep results
                errors = []
                named = {'errors': errors}
                fname = type(curline['condition']).__name__
                v = (curline['condition']).process(*args, **named)

                # Log what happend!
                self.log.debug("  %s: [Filter]  %s(%s) called and returned: %s" % (
                    lptr, fname, ", ".join(map(lambda x : "\"" + x + "\"",  curline['params'])), v))

                # Append the result to the stack.
                stack.append(v)
                if not v:
                    if len(errors):
                        lasterrmsg =  errors.pop()

            # A comparator compares two values from the stack and then returns a single
            #  boolean value.
            elif 'operator' in curline:
                v1 = stack.pop()
                v2 = stack.pop()
                fname = type(curline['operator']).__name__
                res = (curline['operator']).process(v1, v2)
                stack.append(res)

                # Add last error message
                if not res:
                    errormsgs.append(lasterrmsg)
                    lasterrmsg = ""

                # Log what happend!
                self.log.debug("  %s: [OPERATOR]  %s(%s, %s) called and returned: %s" % (
                    lptr, fname, v1, v2, res))

        # Attach last error message
        res = stack.pop()
        if not res and lasterrmsg != "":
            errormsgs.append(lasterrmsg)

        self.log.debug(" <- VALIDATOR ENDED (%s)" % (key))
        return res, errormsgs

    def __processFilter(self, fltr, key, prop):
        """
        This method processes a given process-list (fltr) for a given property (prop).
        For example: When a property has to be stored in the backend, it will
         run through the out-filter-process-list and thus will be transformed into a storable
         key, value pair.
        """

        # Search for replaceable patterns in the process-list.
        fltr = self.__fillInPlaceholders(fltr)

        # This is our process-line pointer it points to the process-list line
        #  we're executing at the moment
        lptr = 0

        # Our filter result stack
        stack = list()

        # Log values
        self.log.debug(" -> FILTER STARTED (%s)" % (key))
        #for pkey in prop:
        #    self.log.debug("  %s: %s: %s" % (lptr, pkey, prop[pkey]['value']))

        # Process the list till we reach the end..
        while (lptr + 1) in fltr:

            # Get the current line and increase the process list pointer.
            lptr = lptr + 1
            curline = fltr[lptr]

            # A filter is used to manipulate the 'value' or the 'key' or maybe both.
            if 'filter' in curline:

                # Build up argument list
                args = [self, key, prop]
                fname = type(curline['filter']).__name__
                for entry in curline['params']:
                    args.append(entry)

                # Process filter and keep results
                try:
                    key, prop = (curline['filter']).process(*args)
                except Exception as e:
                    raise FactoryException("Filter '%s' execution failed for '%s'! Error was: %s" % (fname, key, e))

                # Ensure that the processed data is still valid.
                # Filter may mess things up and then the next cannot process correctly.
                if (key not in prop):
                    raise FactoryException("Filter '%s' returned invalid key property key '%s'!" % (fname, key))

                # Check if the filter returned all expected property values.
                for pk in prop:
                    if not all(k in prop[pk] for k in ('backend', 'value', 'type')):
                        missing = ", ".join(set(['backend', 'value', 'type']) - set(prop[pk].keys()))
                        raise FactoryException("Filter '%s' does not return all expected property values! '%s' missing." % (fname, missing))

                    # Check if the returned value-type is list or None.
                    if type(prop[pk]['value']) not in [list, type(None)]:
                        raise FactoryException("Filter '%s' does not return a 'list' as value for key %s (%s)!" % (
                            fname, pk, type(prop[pk]['value'])))

                self.log.debug("  %s: [Filter]  %s(%s) called " % (lptr, fname, ", ".join(map(lambda x : "\"" + x + "\"",  curline['params']))))

            # A condition matches for something and returns a boolean value.
            # We'll put this value on the stack for later use.
            elif 'condition' in curline:

                # Build up argument list
                args = [key] + curline['params']

                # Process condition and keep results
                stack.append((curline['condition']).process(*args))

                fname = type(curline['condition']).__name__
                self.log.debug("  %s: [Condition] %s(%s) called " % (lptr, fname, ", ".join(curline['params'])))

            # Handle jump, for example if a condition has failed, jump over its filter-chain.
            elif 'jump' in curline:

                # Jump to <line> -1 because we will increase the line ptr later.
                olptr = lptr
                if curline['jump'] == 'conditional':
                    if stack.pop():
                        lptr = curline['onTrue'] - 1
                    else:
                        lptr = curline['onFalse'] - 1
                else:
                    lptr = curline['to'] - 1

                self.log.debug("  %s: [Goto] %s ()" % (olptr, lptr))

            # A comparator compares two values from the stack and then returns a single
            #  boolean value.
            elif 'operator' in curline:
                a = stack.pop()
                b = stack.pop()
                stack.append((curline['operator']).process(a, b))

                fname = type(curline['operator']).__name__
                self.log.debug("  %s: [Condition] %s(%s, %s) called " % (lptr, fname, a, b))

            # Log current values
            #self.log.debug("  result")
            #for pkey in prop:
            #    self.log.debug("   %s: %s" % (pkey, prop[pkey]['value']))

        self.log.debug(" <- FILTER ENDED")
        return prop

    def __fillInPlaceholders(self, fltr):
        """
        This method fill in placeholder into in- and out-filters.
        """

        # Collect all property values
        propList = {}
        props = getattr(self, '__properties')
        for key in props:
            if props[key]['multivalue']:
                propList[key] = props[key]['value']
            else:
                if props[key]['value'] and len(props[key]['value']):
                    propList[key] = props[key]['value'][0]
                else:
                    propList[key] = None

        # An inline function which replaces format string tokens
        def _placeHolder(x):
            for name in propList:
                try:
                    x = x % propList
                except:
                    pass
            return (x)

        # Walk trough each line of the process list an replace placeholders.
        for line in fltr:
            if 'params' in fltr[line]:
                fltr[line]['params'] = map(_placeHolder,
                        fltr[line]['params'])
        return fltr

    def remove(self, recursive=False):
        """
        Removes this object - and eventually it's containements.
        """
        if not self._base_object:
            raise FactoryException("cannot remove non base object - use retract")

        #TODO: notify extension about remove
        #for every used extension:
        #   extension.retract()

        props = getattr(self, '__properties')

        # Collect backends
        backends = [getattr(self, '_backend')]

        for prop, info in props.items():
            if not info['backend'] in backends:
                backends.append(info['backend'])

        # Remove for all backends, removing the primary one as the last one
        backends.reverse()
        obj = self
        if recursive:
            #TODO: emit a "move" signal for all affected objects
            raise NotImplemented("recursive removal is not implemented")
        else:
            zope.event.notify(ObjectChanged("pre remove", obj))

            for backend in backends:
                be = ObjectBackendRegistry.getBackend(backend)
                be.remove(obj.uuid)

            zope.event.notify(ObjectChanged("post remove", obj))

    def move_extension(self, new_base):
        #TODO: do whatever needed to move (or just notify) an extension object
        pass

    def move(self, new_base):
        """
        Moves this object - and eventually it's containements.
        """
        if not self._base_object:
            raise FactoryException("cannot move non base objects")

        props = getattr(self, '__properties')

        #TODO: notify extension about move
        #for every used extension:
        #   extension.move_extension(self.uuid, new_base)

        # Collect backends
        backends = [getattr(self, '_backend')]

        for prop, info in props.items():
            if not info['backend'] in backends:
                backends.append(info['backend'])

        obj = self
        zope.event.notify(ObjectChanged("pre move", obj))

        # Move for all backends (...)
        backends.reverse()
        for backend in backends:
            be = ObjectBackendRegistry.getBackend(backend)
            be.move(self.uuid, new_base)

        #TODO: emit a "move" signal for all affected objects
        zope.event.notify(ObjectChanged("post move", obj))

    def retract(self):
        """
        Removes this object extension
        """
        if self._base_object:
            raise FactoryException("base objects cannot be retracted")

        props = getattr(self, '__properties')

        # Collect backends
        backends = [getattr(self, '_backend')]

        for prop, info in props.items():
            if not info['backend'] in backends:
                backends.append(info['backend'])

        # Retract for all backends, removing the primary one as the last one
        backends.reverse()
        obj = self
        zope.event.notify(ObjectChanged("pre retract", obj))

        for backend in backends:
            be = ObjectBackendRegistry.getBackend(backend)
            r_attrs = self.getExclusiveProperties()
            be.retract(self.uuid, [a for a in r_attrs if getattr(r_attrs, a)], self._backendAttrs[backend])

        zope.event.notify(ObjectChanged("pre retract", obj))

    def _del_(self):
        """
        Internal cleanup method ...
        """
        #TODO
        print "--> cleanup"


class IObjectChanged(Interface):

    def __init__(self, obj):
        pass


class IAttributeChanged(Interface):

    def __init__(self, attr, value):
        pass


class ObjectChanged(object):
    implements(IObjectChanged)

    def __init__(self, reason, obj):
        self.reason = reason
        self.uuid = obj.uuid


class AttributeChanged(object):
    implements(IAttributeChanged)

    def __init__(self, reason, obj, target):
        self.reason = reason
        self.target = target
        self.uuid = obj.uuid
