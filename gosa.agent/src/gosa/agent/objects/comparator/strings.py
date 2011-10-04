# -*- coding: utf-8 -*-
import re
import Levenshtein
from gosa.agent.objects.comparator import ElementComparator


class Like(ElementComparator):

    def __init__(self, obj):
        super(Like, self).__init__()

    def process(self, key, value, match, errors=[]):
        return Levenshtein.distance(value, match) < 4


class RegEx(ElementComparator):

    def __init__(self, obj):
        super(RegEx, self).__init__()

    def process(self, key, value, match, errors=[]):
        return re.match(match, value)


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
                errors.append("Invalid length received for '%s: %s'! At least %s characters are required!" % (
                    str(key), str(entry), minSize))
                return False
            elif maxSize >=0 and len(entry) > maxSize:
                errors.append("Invalid length received for '%s: %s'! A maximum of %s characters are allowed!" % (
                    str(key), str(entry), maxSize))
                return False
        return True


class isString(ElementComparator):

    def __init__(self, obj):
        super(isString, self).__init__()

    def process(self, key, value, errors=[]):
        if type(value) != str:
            errors.append("Invalid type received for '%s: %s'!" % (str(key),
                str(value)))
            return False
        return True

