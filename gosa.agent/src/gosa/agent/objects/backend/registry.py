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


def get_backend(obj, backend):
    if not backend:
        backend = obj._backend
    return ObjectBackendRegistry.getBackend(backend)

def load(obj, keys, backend=None):
    backendI = get_backend(obj, backend)
    return backendI.load(obj.uuid, keys)

def update(obj, data, backend=None):
    backendI = get_backend(obj, backend)
    return backendI.update(obj.uuid, data)

def create(obj, data, backend=None, backend_attrs=None):
    backendI = get_backend(obj, backend)
    return backendI.create(obj.dn, data, backend_attrs)

def extend(obj, data, backend=None, backend_attrs=None, foreign_keys=None):
    backendI = get_backend(obj, backend)
    return backendI.extend(obj.dn, data, backend_attrs, foreign_keys)

def remove(obj, backend=None, backend_attrs=None):
    return remove_by_uuid(obj.uuid, backend, backend_attrs)

def retract(obj, backend=None, backend_attrs=None, foreign_keys=None):
    return backendI.retract(obj.uuid, False)

def remove_by_uuid(uuid, backend=None, backend_attrs=None):
    backendI = get_backend(obj, backend)
    return backendI.remove(obj.uuid, False)

def move(obj, new_base, backend=None, backend_attrs=None):
    backendI = get_backend(obj, backend)
    return backendI.move(obj.uuid, new_base)
