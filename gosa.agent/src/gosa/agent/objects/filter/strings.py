# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter


class ConcatString(ElementFilter):

    def __init__(self, obj):
        super(ConcatString, self).__init__(obj)

    def process(self, obj, key, value, appstr, position):

        new_val = {}
        if position == "right":
            new_val = map(lambda x: x + appstr, value[key])
        else:
            new_val = map(lambda x: appstr + x, value[key])
        return key, {key: new_val}
