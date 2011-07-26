# -*- coding: utf-8 -*-
from gosa.agent.objects.comparator import ElementComparator


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
