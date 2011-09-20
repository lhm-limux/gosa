# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter


class ConcatString(ElementFilter):

    def __init__(self, obj):
        super(ConcatString, self).__init__(obj)

    def process(self, obj, key, value, appstr, position):

        new_val = value[key]
        if type(value[key]) in [str, unicode]:
            if position == "right":
                new_val = value[key] + appstr
            else:
                new_val = appstr + value[key]

        elif type(value[key]) in [dict, list]:
            new_val = {}
            if position == "right":
                new_val = map(lambda x: x + appstr, value[key])
            else:
                new_val = map(lambda x: appstr + x, value[key])
        else:
            raise ValueError("Unknown input type for filter %s. Type as '%s'!") % (
                    self.__class__.__name__, type(value))
        return key, {key: new_val}
