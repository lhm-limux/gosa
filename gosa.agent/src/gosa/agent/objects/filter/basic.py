# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter, ElementFilterException
import copy

class Target(ElementFilter):

    def __init__(self, obj):
        super(Target, self).__init__(obj)

    def process(self, obj, key, valDict, new_key):
        if key != new_key:
            valDict[new_key] = valDict[key]
            del(valDict[key])
        return new_key, valDict


class SetBackend(ElementFilter):

    def __init__(self, obj):
        super(SetBackend, self).__init__(obj)

    def process(self, obj, key, valDict, new_backend):
        valDict[key]['backend'] = new_backend
        return key, valDict


class SetValue(ElementFilter):

    def __init__(self, obj):
        super(SetValue, self).__init__(obj)

    def process(self, obj, key, valDict, value, vtype="String"):
        if vtype == "String":
            valDict[key]['value'] = str(value)
        else:
            raise ElementFilterException("Invalid type value (%s) given for filter '%s'!" % (vtype,'SetValue'))
        return key, valDict


#class LoadAttr(ElementFilter):
#
#    def __init__(self, obj):
#        super(LoadAttr, self).__init__(obj)
#
#    def process(self, obj, key, value, attr):
#        #FIXME
#        return key, 854711
#
#
#class SaveAttr(ElementFilter):
#
#    def __init__(self, obj):
#        super(SaveAttr, self).__init__(obj)
#
#    def process(self, obj, key, value):
#        return key, value


class Clear(ElementFilter):

    def __init__(self, obj):
        super(Clear, self).__init__(obj)

    def process(self, obj, key, valDict):

        if type(valDict[key]['value']) in [str, unicode]:
            valDict[key]['value'] = ''
            return key, valDict
        elif type(valDict[key]['value']) in [dict, list]:
            valDict[key]['value'] = ['']
            return key, valDict
        else:
            raise ValueError("Unknown input type for filter %s. Type as '%s'!" % (
                    self.__class__.__name__, type(value)))
