# -*- coding: utf-8 -*-
import re
import Levenshtein
from gosa.agent.objects.comparator import ElementComparator


class Like(ElementComparator):
    """
    Object property validator which checks if a given property value is
    like a given operand.

    =========== ==================
    Key         Description
    =========== ==================
    match       The value we match againt.
    =========== ==================
    """

    def __init__(self, obj):
        super(Like, self).__init__()

    def process(self, key, value, match, errors=[]):

        # All items of value have to match.
        cnt = 0
        for item in value:
            if Levenshtein.distance(unicode(item), unicode(match)) >= 4:
                errors.append("Item %s (%s) is not like '%s'!" % (cnt, item, match))
                return False
            cnt += 1
        return True


class RegEx(ElementComparator):
    """
    Object property validator which checks if a given property matches
    a given regular expression.

    =========== ==================
    Key         Description
    =========== ==================
    match       The value we match againt.
    =========== ==================
    """

    def __init__(self, obj):
        super(RegEx, self).__init__()

    def process(self, key, value, match, errors=[]):

        # All items of value have to match.
        cnt = 0
        for item in value:
            if not re.match(match, item):
                errors.append("Item %s (%s) does not match the regular expression '%s'!" % (cnt, item, match))
                return False
            cnt += 1
        return True


class stringLength(ElementComparator):
    """
    Object property validator which checks for a given value length.

    ======= ==================
    Key     Description
    ======= ==================
    minSize The minimum-size of the property values.
    maxSize The maximum-size of the property values.
    ======= ==================

    """
    def __init__(self, obj):
        super(stringLength, self).__init__()

    def process(self, key, value, minSize, maxSize, errors=[]):

        # Convert limits to integer values.
        minSize = int(minSize)
        maxSize = int(maxSize)

        # Each item of value has to match the given length-rules
        for entry in value:
            if minSize >= 0 and len(entry) < minSize:
                errors.append("Item %s (%s) is to small, at least %s characters are required!" % (cnt, item, minSize))
                return False
            elif maxSize >=0 and len(entry) > maxSize:
                errors.append("Item %s (%s) is to great, at max %s characters are allowed!" % (cnt, item, maxSize))
                return False
        return True
