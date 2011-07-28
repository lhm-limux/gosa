# -*- coding: utf-8 -*-
from gosa.agent.objects.comparator import ElementComparator


class Equals(ElementComparator):

    def __init__(self, obj):
        super(Equals, self).__init__()

    def process(self, key, value, match, case_ignore=False, errors=[]):
        if case_ignore:
            return value.lower() == match.lower()

        return value == match


class Greater(ElementComparator):

    def __init__(self, obj):
        super(Greater, self).__init__()

    def process(self, key, value, match, errors=[]):
        return value > match


class Smaller(ElementComparator):

    def __init__(self, obj):
        super(Smaller, self).__init__()

    def process(self, key, value, match, errors=[]):
        return value < match
