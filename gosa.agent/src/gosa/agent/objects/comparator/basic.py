# -*- coding: utf-8 -*-
from gosa.agent.objects.comparator import ElementComparator


class Equals(ElementComparator):
    """
    Object property validator which checks for a given property value.

    =========== ==================
    Key         Description
    =========== ==================
    match       The value we want to match for.
    case_ignore If True then upper/lower case is ignored.
    =========== ==================
    """

    def __init__(self, obj):
        super(Equals, self).__init__()

    def process(self, key, value, match, case_ignore=False, errors=[]):

        # Check each property value
        cnt = 0
        for item in value:

            # Depending on the ignore-case parameter we do not match upper/lower-case differences.
            if case_ignore:
                if item.lower() != match.lower():
                    errors.append("Item %s (%s) did not match the given value '%s'! (ignore case)" % (
                        cnt, item, match))
                    return False
            else:
                if item != match:
                    errors.append("Item %s (%s) did not match the given value '%s'!" % (
                        cnt, item, match))
                    return False
            cnt += 1
        return True


class Greater(ElementComparator):
    """
    Object property validator which checks if a given property value is
    greater than a given operand.

    =========== ==================
    Key         Description
    =========== ==================
    match       The value we match againt.
    =========== ==================
    """

    def __init__(self, obj):
        super(Greater, self).__init__()

    def process(self, key, value, match, errors=[]):

        # All items of value have to match.
        cnt = 0
        match = int(match)
        for item in value:
            item = int(item)
            if not (item > match):
                errors.append("Item %s (%s) is not greater then %s!" % (cnt, item, match))
                return False
            cnt += 1
        return True


class Smaller(ElementComparator):

    """
    Object property validator which checks if a given property value is
    smaller than a given operand.

    =========== ==================
    Key         Description
    =========== ==================
    match       The value we match againt.
    =========== ==================
    """
    def __init__(self, obj):
        super(Smaller, self).__init__()

    def process(self, key, value, match, errors=[]):

        # All items of value have to match.
        match = int(match)
        cnt = 0
        for item in value:
            item = int(item)
            if not (item < match):
                errors.append("Item %s (%s) is not smaller then %s!" % (cnt, item, match))
                return False
            cnt += 1
        return True
