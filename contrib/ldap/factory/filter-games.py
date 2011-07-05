# -*- coding: utf-8 -*-
import re
import datetime
import Levenshtein
from time import mktime

class ElementFilter(object):

    def __init__(self, obj):
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


class ElementComparator(object):

    def __init(self, obj):
        pass

    def process(self, *args, **kwargs):
        raise NotImplementedError("not implemented")


class Equals(ElementComparator):

    def __init__(self, obj):
        super(Equals, self).__init__()

    def process(self, a, b, case_ignore=False):
        if case_ignore:
            return a.lower() == b.lower()

        return a == b


class Greater(ElementComparator):

    def __init__(self, obj):
        super(Greater, self).__init__()

    def process(self, a, b):
        return a > b


class Smaller(ElementComparator):

    def __init__(self, obj):
        super(Smaller, self).__init__()

    def process(self, a, b):
        return a < b


class Like(ElementComparator):

    def __init__(self, obj):
        super(Like, self).__init__()

    def process(self, a, b):
        return Levenshtein.distance(a, b) < 4


class RegEx(ElementComparator):

    def __init__(self, obj):
        super(RegEx, self).__init__()

    def process(self, a, b):
        return re.match(a, b)


class ToUnixTime(ElementFilter):

    def __init__(self, obj):
        super(ToUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        value = mktime(value.timetuple())
        return key, int(value)


class FromUnixTime(ElementFilter):

    def __init__(self, obj):
        super(FromUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        value = datetime.datetime.fromtimestamp(value)
        return key, value



class Target(ElementFilter):

    def __init__(self, obj):
        super(Target, self).__init__(obj)

    def process(self, obj, key, value, new_key):
        key = new_key
        return key, value


class Load(ElementFilter):

    def __init__(self, obj):
        super(Load, self).__init__(obj)

    def process(self, obj, key, value, attr):
        return key, 854711



# --- Prepare

class dummy(object):

    cn = "Cajus Pollmeier"
    givenName = "Cajus"
    sn = "Pollmeier"
    uid = "cajus"
    tm = datetime.datetime.now()

o = dummy()

# --- Comparator test

e = Equals(o)
el = Like(o)
print "99 == 12", e.process(99, 12)
print "88 == 88", e.process(88, 88)
print "Klaus == Claus", el.process("Klaus", "Claus")
exit()


# --- Out test
t = ToUnixTime(o)
f = FromUnixTime(o)
s = Target(o)
l = Load(o)

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
