# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter
import re

class HashPassword(ElementFilter):

    def __init__(self, obj):
        super(HashPassword, self).__init__(obj)

    def process(self, obj, key, valDict, method):
        if type(valDict[key]['value']) in [str, unicode]:
            valDict[key]['value'] = "{%s}%s" % (method, valDict[key]['value'])
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict

class SambaHash(ElementFilter):

    def __init__(self, obj):
        super(SambaHash, self).__init__(obj)

    def process(self, obj, key, valDict):
        if type(valDict[key]['value']) in [str, unicode]:
            valDict['sambaNTPassword'] = {
                    'value': 'blabla',
                    'backend': valDict[key]['backend'],
                    'type': valDict[key]['type']}
            valDict['sambaLMPassword'] = {
                    'value': 'blabla',
                    'backend': valDict[key]['backend'],
                    'type': valDict[key]['type']}
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict
