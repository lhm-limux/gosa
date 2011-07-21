# -*- coding: utf-8 -*-

class ObjectBackend(object):

    def loadAttrs(self, uuid, key):
        raise NotImplementedError("object backend is missing loadAttr()")

    def dn2uuid(self, dn):
        raise NotImplementedError("object backend is not capable of mapping DN to UUID")
