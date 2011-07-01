# -*- coding: utf-8 -*-


class ObjectBackendRegistry(object):
    instance = None
    backends = {}
    uuidAttr = "entryUUID"

    def __init__(self):
        # Load available backends
        #TODO: this is hard coded LDAP stuff in the moment,
        #      load from configuration later on
        from back_ldap import LDAPBackend
        ObjectBackendRegistry.backends['LDAP'] = LDAPBackend()

    def dn2uuid(self, backend, dn):
        return ObjectBackendRegistry.backends[backend].dn2uuid(dn)

    @staticmethod
    def getInstance():
        if not ObjectBackendRegistry.instance:
            ObjectBackendRegistry.instance = ObjectBackendRegistry()

        return ObjectBackendRegistry.instance

    @staticmethod
    def getBackend(name):
        if not name in ObjectBackendRegistry.backends:
            raise ValueError("no such backend '%s'" % name)

        return ObjectBackendRegistry.backends[name]


def loadAttr(obj, key):
    backend = ObjectBackendRegistry.getBackend(obj._backend)
    return backend.loadAttr(obj.uuid, key)
