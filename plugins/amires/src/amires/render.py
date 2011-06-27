# -*- coding: utf-8 -*-

class BaseRenderer(object):

    priority = 1

    def __init__(self):
        pass

    def getHTML(self, particiantInfo):
        if not particiantInfo:
            raise RuntimeError("particiantInfo must not be None.")
        if type(particiantInfo) is not dict:
            raise TypeError("particiant Info must be a dictionary.")
