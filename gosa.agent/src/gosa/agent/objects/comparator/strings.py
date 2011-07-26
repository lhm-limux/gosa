# -*- coding: utf-8 -*-
import re
import Levenshtein
from gosa.agent.objects.comparator import ElementComparator


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
