# -*- coding: utf-8 -*-

class EntryNotUnique(Exception):
    pass


class EntryNotFound(Exception):
    pass


class ObjectBackend(object):

    def loadAttrs(self, uuid, keys):
        raise NotImplementedError("object backend is missing loadAttrs()")

    def saveAttrs(self, uuid, data):
        raise NotImplementedError("object backend is missing saveAttrs()")

    def dn2uuid(self, dn):
        raise NotImplementedError("object backend is not capable of mapping DN to UUID")
