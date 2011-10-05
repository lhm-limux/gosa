# -*- coding: utf-8 -*-
import pkg_resources


class ObjectBackendRegistry(object):
    instance = None
    backends = {}
    uuidAttr = "entryUUID"

    def __init__(self):
        # Load available backends
        for entry in pkg_resources.iter_entry_points("gosa.object.backend"):
            clazz = entry.load()
            ObjectBackendRegistry.backends[clazz.__name__] = clazz()

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


def load(obj, keys, backend=None):
    if not backend:
        backend = obj._backend

    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.load(obj.uuid, keys)


def update(obj, data, backend=None):
    if not backend:
        backend = obj._backend

    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.update(obj.uuid, data)

def create(obj, data, backend=None, backend_attrs=None):
    if not backend:
        backend = obj._backend

    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.create(obj.dn, data, backend_attrs)

def extend(obj, data, backend=None, backend_attrs=None, foreign_keys=None):
    if not backend:
        backend = obj._backend

    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.extend(obj.dn, data, backend_attrs, foreign_keys)

def remove(obj, backend=None, backend_attrs=None):
    if not backend:
        backend = obj._backend

    return remove_by_uuid(obj.uuid)

def remove_by_uuid(uuid, backend):
    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.remove(obj.uuid, False)

def move(obj, new_base, backend=None, backend_attrs=None):
    if not backend:
        backend = obj._backend

    backendI = ObjectBackendRegistry.getBackend(backend)
    return backendI.move(obj.uuid, new_base)
