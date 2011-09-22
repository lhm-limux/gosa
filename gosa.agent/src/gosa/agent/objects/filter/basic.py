# -*- coding: utf-8 -*-
from gosa.agent.objects.filter import ElementFilter


class Target(ElementFilter):

    def __init__(self, obj):
        super(Target, self).__init__(obj)

    def process(self, obj, key, value, new_key):
        new_val = {new_key: value[key]}
        key = new_key
        return key, new_val


class LoadAttr(ElementFilter):

    def __init__(self, obj):
        super(LoadAttr, self).__init__(obj)

    def process(self, obj, key, value, attr):
        #FIXME
        return key, 854711


class SaveAttr(ElementFilter):

    def __init__(self, obj):
        super(SaveAttr, self).__init__(obj)

    def process(self, obj, key, value):
        return key, value


class Clear(ElementFilter):

    def __init__(self, obj):
        super(Clear, self).__init__(obj)

    def process(self, obj, key, value):

        if type(value[key]) in [str, unicode]:
            return key, {key: ''}
        elif type(value[key]) in [dict, list]:
            return key, {key: ['']}
        else:
            raise ValueError("Unknown input type for filter %s. Type as '%s'!" % (
                    self.__class__.__name__, type(value)))
