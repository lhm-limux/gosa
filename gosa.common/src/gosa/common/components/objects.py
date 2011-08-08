# -*- coding: utf-8 -*-
import pkg_resources
from gosa.common import Environment


class ObjectRegistry(object):
    """
    Object registry class. The registry holds object instances
    that are currently in use by clients. Objects can be either
    registered manually using::

        >>> from gosa.common.components import ObjectRegistry
        >>> ObjectRegistry.register("the.unique.object.oid", ObjectToRegister)

    The preferred way to register objects is to use the setuptools
    section ```[gosa.objects]```::

        [gosa.objects]
        the.unique.object.oid = full.path.to.the:ObjectToRegister

    In this case, all objects are registered after the agent is fired
    up automatically.
    """
    _objects = {}
    _instance = None

    def __init__(self):
        for entry in pkg_resources.iter_entry_points('gosa.objects'):
            ObjectRegistry.register(entry.name, entry.load())

    @staticmethod
    def register(oid, obj):
        """
        Register the given object at the provided OID.
        """
        if oid in  ObjectRegistry._objects:
            raise ValueError("OID '%s' is already registerd!" % oid)

        env = Environment.getInstance()
        env.log.debug("registered object OID '%s'" % oid)
        ObjectRegistry._objects[oid] = {
            'object': obj,
            'signature': None}

    @staticmethod
    def getInstance():
        """
        Act as a singleton and return an instance of ObjectRegistry.
        """
        if not ObjectRegistry._instance:
            ObjectRegistry._instance = ObjectRegistry()

        return ObjectRegistry
