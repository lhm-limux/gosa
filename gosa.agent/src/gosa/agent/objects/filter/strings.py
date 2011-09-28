# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter
import re

class ConcatString(ElementFilter):

    def __init__(self, obj):
        super(ConcatString, self).__init__(obj)

    def process(self, obj, key, valDict, appstr, position):
        if type(valDict[key]['value']) in [str, unicode]:
            if position == "right":
                new_val = valDict[key]['value'] + appstr
            else:
                new_val = appstr + valDict[key]['value']
            valDict[key]['value'] = new_val
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict

class Replace(ElementFilter):

    def __init__(self, obj):
        super(Replace, self).__init__(obj)

    def process(self, obj, key, valDict, regex, replacement):
        if type(valDict[key]['value']) in [str, unicode]:
            valDict[key]['value'] = re.sub(regex, str(replacement), valDict[key]['value'])
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict
