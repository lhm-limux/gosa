# -*- coding: utf-8 -*-
import datetime
from time import mktime
from gosa.agent.objects.filter import ElementFilter


class ToUnixTime(ElementFilter):

    def __init__(self, obj):
        super(ToUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        new_val = map(lambda x: mktime(x.timetuple()), value[key])
        return key, {key: new_val}


class FromUnixTime(ElementFilter):

    def __init__(self, obj):
        super(FromUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        new_val = map(lambda x: datetime.datetime.fromtimestamp(x), value[key])
        return key, {key: new_val}
