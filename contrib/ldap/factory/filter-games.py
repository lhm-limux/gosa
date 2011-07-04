# -*- coding: utf-8 -*-
import datetime
from time import mktime

class ElementFilter(object):

    def __init__(self):
        #TODO: load parameters
        #      decide what we "need"
        pass

    def process(self, obj, key, value):
        raise NotImplementedError("not implemented")

    def getReferences(self):
        """
        Return the properties we reference to. This makes us speed up
        value loading, because we cann pull everything we need in one step.
        """
        return {}


class ToUnixTime(ElementFilter):

    def __init__(self):
        super(ToUnixTime, self).__init__()

    def process(self, obj, key, value):
        value = mktime(value.timetuple())
        return key, int(value)


class FromUnixTime(ElementFilter):

    def __init__(self):
        super(FromUnixTime, self).__init__()

    def process(self, obj, key, value):
        value = datetime.datetime.fromtimestamp(value)
        return key, value



class Target(ElementFilter):

    def __init__(self):
        super(Target, self).__init__()

    def process(self, obj, key, value, new_key):
        key = new_key
        return key, value


class Load(ElementFilter):

    def __init__(self):
        super(Load, self).__init__()

    def process(self, obj, key, value, attr):
        return key, 854711


# --- Out test

class dummy(object):

    cn = "Cajus Pollmeier"
    givenName = "Cajus"
    sn = "Pollmeier"
    uid = "cajus"
    tm = datetime.datetime.now()

o = dummy()
t = ToUnixTime()
f = FromUnixTime()
s = Target()
l = Load()

key = "tm"
value = o.tm
key, value = t.process(o, key, value)
key, value = s.process(o, key, value, "sambaLogoffTime")

print "%s=%s" % (key, value)


# --- In test

key = "tm"
value = None
key, value = l.process(o, key, value, "sambaLogoffTime")
key, value = f.process(o, key, value)
print "%s=%s" % (key, str(value))
