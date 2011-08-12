# -*- coding: utf-8 -*-
"""
...
"""
import uuid
from types import MethodType
from gosa.common import Environment
from gosa.common.components import Command, PluginRegistry, ObjectRegistry
from gosa.common.utils import N_


class JSONRPCObjectMapper(object):
    """
    Plugin to map jsonrpc object manager
    """
    _target_ = 'core'

    #TODO: move store to object registry using memcache, DB or whatever
    #      to allow shared objects accross agent instances, maybe it's
    #      better to move all the stuff to the ObjectRegistry.
    __store = {}
    __proxy = {}

    @Command(__help__=N_("Close object and remove it from stack"))
    def closeObject(self, ref):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)

        del JSONRPCObjectMapper.__store[ref]

    @Command(__help__=N_("Set property for object on stack"))
    def setObjectProperty(self, ref, name, value):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not name in JSONRPCObjectMapper.__store[ref]['properties']:
            raise ValueError("property %s not found" % name)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.setObjectProperty(ref, name, value)

        return setattr(JSONRPCObjectMapper.__store[ref]['object'], name, value)

    @Command(__help__=N_("Get property from object on stack"))
    def getObjectProperty(self, ref, name):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not name in JSONRPCObjectMapper.__store[ref]['properties']:
            raise ValueError("property %s not found" % name)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.getObjectProperty(ref, name)

        return getattr(JSONRPCObjectMapper.__store[ref]['object'], name)

    @Command(__help__=N_("Call method from object on stack"))
    def dispatchObjectMethod(self, ref, method, *args):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not method in JSONRPCObjectMapper.__store[ref]['methods']:
            raise ValueError("method %s not found" % method)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.dispatchObjectMethod(ref, method, *args)

        return getattr(JSONRPCObjectMapper.__store[ref]['object'], method)(*args)

    @Command(__help__=N_("Instantiate object and place it on stack"))
    def openObject(self, oid, *args, **kwargs):
        if not self.__can_oid_be_handled_locally(oid):
            proxy = self.__get_proxy_by_oid(oid)
            return proxy.openObject(oid, *args)

        env = Environment.getInstance()

        # Use oid to find the object type
        obj_type = self.__get_object_type(oid)
        methods, properties = self.__inspect(obj_type)

        # Load instance, fill with dummy stuff
        ref = str(uuid.uuid1())

        # Make object instance and store it
        obj = obj_type(*args, **kwargs)
        JSONRPCObjectMapper.__store[ref] = {
                'node': env.id,
                'oid': oid,
                'object': obj,
                'methods': methods,
                'properties': properties}

        # Build property dict
        propvals = {}
        if properties:
            propvals = dict(map(lambda p: (p, getattr(obj, p)), properties))

        # Build result
        result = {"__jsonclass__":["json.ObjectFactory", [obj_type.__name__, ref, oid, methods, properties]]}
        result.update(propvals)

        return result

    def __get_object_type(self, oid):
        if not oid in ObjectRegistry.objects:
            raise ValueError("Unknown object OID %s" % oid)

        return ObjectRegistry.objects[oid]['object']

    def __inspect(self, clazz):
        methods = []
        properties = []

        for part in dir(clazz):
            if part.startswith("_"):
                continue
            obj = getattr(clazz, part)
            if isinstance(obj, MethodType):
                methods.append(part)
            if isinstance(obj, property):
                properties.append(part)

        return methods, properties

    def __can_be_handled_locally(self, ref):
        return self.__can_oid_be_handled_locally(
                JSONRPCObjectMapper.__store[ref]['oid'])

    def __can_oid_be_handled_locally(self, oid):
        cr = PluginRegistry.getInstance('CommandRegistry')
        if not oid in cr.objects:
            raise ValueError("Unknown object OID %s" % oid)
        return oid in ObjectRegistry.objects

    def __get_proxy(self, ref):
        return self.__get_proxy_by_oid(
                JSONRPCObjectMapper.__store[ref]['oid'])

    def __get_proxy_by_oid(self, oid):
        # Choose a possible node
        cr = PluginRegistry.getInstance('CommandRegistry')
        nodes = cr.get_load_sorted_nodes()

        # Get first match that is a provider for this object
        for provider in nodes.keys():
            if provider in cr.objects[oid]:
                break

        if not provider in self.__proxy:
            env = Environment.getInstance()
            queue = '%s.core.%s' % (env.domain, provider)
            amqp = PluginRegistry.getInstance("AMQPHandler")
            self.__proxy[provider] = AMQPServiceProxy(amqp.url['source'], queue)

        return self.__proxy[provider]
