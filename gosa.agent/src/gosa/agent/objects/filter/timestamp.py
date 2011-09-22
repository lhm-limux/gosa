# -*- coding: utf-8 -*-
import datetime
from time import mktime
from gosa.agent.objects.filter import ElementFilter


class ToUnixTime(ElementFilter):

    def __init__(self, obj):
        super(ToUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        new_val = [mktime(x.timetuple()) for x in value[key]]
        return key, {key: new_val}


class FromUnixTime(ElementFilter):

    def __init__(self, obj):
        super(FromUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        new_val = [datetime.datetime.fromtimestamp(x) for x in value[key]]
        return key, {key: new_val}
