# -*- coding: utf-8 -*-
from gosa.agent.objects.operator import ElementOperator


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
