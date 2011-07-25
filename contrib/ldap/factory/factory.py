# -*- coding: utf-8 -*-
import os
import time
import datetime
import re
from lxml import etree, objectify
from backend.registry import ObjectBackendRegistry, loadAttrs
from filters import *

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
                out_f = self.__build_filter(prop['OutFilter'])
                if 'Backend' in prop['OutFilter'].__dict__:
                    out_b = str(prop['OutFilter']['Backend'])
                else:
                    out_b = str(classr.DefaultBackend)

                # Do we have a input filter definition?
                in_f = None
                #in_f = self.__build_filter(prop['InFilter'])
                if 'Backend' in prop['InFilter'].__dict__:
                    in_b = str(prop['InFilter']['Backend'])
                else:
                    out_b = str(classr.DefaultBackend)

                syntax = str(prop['Syntax'])
                props[str(prop['Name'])] = {
                        'value': None,
                        'name': str(prop['Name']),
                        'orig': None,
                        'status': STATUS_OK,
                        'type': TYPE_MAP[syntax],
                        'syntax': syntax,
                        'out_filter': out_f,
                        'out_backend': out_b,
                        'in_filter': in_f,
                        'in_backend': in_b,
                        'multivalue': bool(prop['MultiValue'])}

                #-----------------
                #validators....
                #-----------------

            for method in classr['Methods']['Method']:
                name = str(method['Name'])

                def funk(*args, **kwargs):
                    variables = {'title': args[0], 'message': args[1]}
                    self.__exec(unicode(str(method['Code']).strip()), variables)

                methods[name] = {
                        'ref': funk}

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

    def __build_filter(self, element, out=None):
        """
        Converts an XML etree element into a process list.
        This list can then be easily executed line by line for each property.
        """

        # Parse each <FilterChain>
        out = {}
        for el in element.iterchildren():
            out = self.__handleFilterChain(el, out)

        return out

    def __handleFilterChain(self, element, out):
        """
        This method is used in '__build_filter' to generate a process
        list for the in and out filters.

        The 'FilterChain' element is handled here.

        Occurrence: OutFilter->FilterChain
        """

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
        if name in globals():
            out[cnt] = {'filter': globals()[name](self), 'params': params}
        else:
            raise Exception("No filter method defined for '%s'!" % (name))
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
            out[cnt + 1] = {'operator': Or(self)}
        else:
            out[cnt + 1] = {'operator': And(self)}

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
        out[cnt] = {'condition': globals()[name](self), 'params': params}
        return(out)


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
                dst = loadAttrs(obj, [key])[0] if 'MultiValue' in props[key] and \
                    not props[key]['MultiValue'] else loadAttrs(obj, [key])

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
        props = getattr(self, '__properties')

        toStore = {}
        for key in props:
            value = props[key]['value']
            if props[key]['out_filter']:
                key, value = self.__processFilter(props[key]['out_filter'], props[key])

            if not props[key]['out_backend'] in toStore:
                toStore[props[key]['out_backend']] = {}
            toStore[props[key]['out_backend']][key] = value

        print "\n\n---- Saving ----"
        for store in toStore:
            print " |-> %s (Backend)" % store
            for entry in toStore[store]:
                print "   |-> %s: " % entry, toStore[store][entry]

        # Schauen was sich so alles verändert hat, dann nach backend getrennt
        # in ein dict packen

    def delete(self):
        print "--> built in delete method"

    def revert(self):
        print "--> built in revert method"
        # Alle CHANGED attribute wieder zurück auf "old" setzen

    def __processFilter(self, fltr, prop):
        """
        This method processes a given process-list (fltr) for a given property (prop).
        For example: When a property has to be stored in the backend, it will
         run through the process list and thus will be transformed into a storable
         key, value pair.
        """

        # This is our process-line pointer it points to the process-list line
        #  we're executing at the moment
        lptr = 0

        # Read current key, value
        key = prop['name']
        value = prop['value']

        orig_value = value
        orig_key = key

        print "+" * 40
        for entry in fltr:
            print entry, fltr[entry]
        print "+" * 40

        # Our filter result stack
        stack = list()

        # Process the list till we reach the end..
        while (lptr + 1) in fltr:

            # Get the current line and increase the process list pointer.
            lptr = lptr + 1
            curline = fltr[lptr]

            # A filter is used to manipulate the 'value' or the 'key' or maybe both.
            if 'filter' in curline:

                # Build up argument list
                args = [self, key, value]
                for entry in curline['params']:
                    args.append(entry)

                # Process filter and keep results
                key, value = (curline['filter']).process(*args)

            # A condition matches for something and returns a boolean value.
            # We'll put this value on the stack for later use.
            elif 'condition' in curline:

                # Build up argument list
                args = curline['params']

                # Process filter and keep results
                stack.append((curline['condition']).process(*args))

            # Handle jump, for example if a condition has failed, jump over its filter-chain.
            elif 'jump' in curline:

                # Jump to <line> -1 because we will increase the line ptr later.
                if curline['jump'] == 'conditional':
                    if stack.pop():
                        lptr = curline['onTrue'] - 1
                    else:
                        lptr = curline['onFalse'] - 1
                else:
                    lptr = curline['to'] - 1

            # A comparator compares two values from the stack and then returns a single
            #  boolean value.
            elif 'operator' in curline:
                stack.append((curline['operator']).process(stack.pop(), stack.pop()))

        #print "-" * 40
        #print "--> Vorher: ", orig_key, orig_value
        #print "--> Nachher: ", key, value

        return key, value
