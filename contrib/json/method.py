# -*- coding: utf-8 -*-


class BaseInstallMethod(object):

    def __init__(self, data):
        self.data = data

    def getBootConfiguration(self):
        return None

    def getBootString(self):
        return None
