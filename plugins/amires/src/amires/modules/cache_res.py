# -*- coding: utf-8 -*-
import copy
import time
from lxml import etree
from amires.resolver import PhoneNumberResolver


class CacheNumberResolver (PhoneNumberResolver):

    priority = 0

    def __init__(self):
        super(CacheNumberResolver, self).__init__()
        self.cache = {}

    def resolve(self, number):
        if number in self.cache:
            item = self.cache[number]

            if not self.hasExpired(item):
                return item
            else:
                del self.cache[number]
                return None
        else:
            return None

    def hasExpired(self, item):
        return item['ttl'] + item['timestamp'] < time.time()

    def cacheNumber(self, item, number):
        if number in self.cache and \
            not self.hasExpired(self.cache[number]):
            return

        if item['ttl'] <= 0.0:
            return

        self.cache[number] = copy.deepcopy(item)
        self.cache[number]['resource'] = self.__class__.__name__

    def removeNumber(self, number):
        if number in self.cache:
            del self.cache[number]
            
    def collectGarbage(self):
        t = time.time()
        res = {}
        for i in self.cache:
            if not self.hasExpired(self.cache[i]):
                res[i] = self.cache[i]

