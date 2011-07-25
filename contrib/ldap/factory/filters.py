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


class ElementComparator(object):

    def __init(self, obj):
        pass

    def process(self, *args, **kwargs):
        raise NotImplementedError("not implemented")


class ElementOperator(object):

    def __init(self, obj):
        pass

    def process(self, *args, **kwargs):
        raise NotImplementedError("not implemented")


class And(ElementOperator):

    def __init__(self, obj):
        super(And, self).__init__()

    def process(self, v1, v2):
        return v1 and v2


class Or(ElementOperator):

    def __init__(self, obj):
        super(Or, self).__init__()

    def process(self, v1, v2):
        return v1 or v2


class Not(ElementOperator):

    def __init__(self, obj):
        super(Not, self).__init__()

    def process(self, a):
        return not a


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
        new_val = map(lambda x: mktime(x.timetuple()), value[key])
        return key, {key: new_val}


class FromUnixTime(ElementFilter):

    def __init__(self, obj):
        super(FromUnixTime, self).__init__(obj)

    def process(self, obj, key, value):
        new_val = map(lambda x: datetime.datetime.fromtimestamp(x), value[key])
        return key, {key: new_val}


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


class SaveAttr(ElementFilter):

    def __init__(self, obj):
        super(SaveAttr, self).__init__(obj)

    def process(self, obj, key, value):
        return key, value


class Clear(ElementFilter):

    def __init__(self, obj):
        super(Clear, self).__init__(obj)

    def process(self, obj, key, value):
        return key, {key: []}


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
