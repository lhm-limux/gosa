# -*- coding: utf-8 -*-
import uuid
from types import MethodType
from gosa.common import Environment
from gosa.common.utils import N_
from gosa.common.components import Command, PluginRegistry, ObjectRegistry, AMQPServiceProxy, Plugin


class JSONRPCObjectMapper(Plugin):
    """
    The *JSONRPCObjectMapper* is a GOsa agent plugin that implements a stack
    which can handle object instances. These can be passed via JSONRPC using
    the *__jsonclass__* helper attribute and allows remote proxies to emulate
    the object on the stack. The stack can hold objects that have been
    retrieved by their *OID* using the :class:`gosa.common.components.objects.ObjectRegistry`.

    Example::

        >>> from gosa.common.components import AMQPServiceProxy
        >>> # Create connection to service
        >>> proxy = AMQPServiceProxy('amqps://admin:secret@amqp.example.net/org.gosa')
        >>> pm = proxy.openObject('libinst.diskdefinition')
        >>> pm.getDisks()
        []
        >>> proxy.closeObject(str(pm))
        >>>

    This will indirectly use the object mapper on the agent side.
    """
    _target_ = 'core'

    #TODO: move store to object registry using memcache, DB or whatever
    #      to allow shared objects accross agent instances, maybe it's
    #      better to move all the stuff to the ObjectRegistry.
    __store = {}
    __proxy = {}

    @Command(__help__=N_("List available object OIDs"))
    def listObjectOIDs(self):
        """
        Provide a list of domain wide available object OIDs.

        ``Return:`` list
        """
        cr = PluginRegistry.getInstance('CommandRegistry')
        return cr.objects.keys()

    @Command(__help__=N_("Close object and remove it from stack"))
    def closeObject(self, ref):
        """
        Close an object by its reference. This will free the object on
        the agent side.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        ref               UUID / object reference
        ================= ==========================
        """
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)

        del JSONRPCObjectMapper.__store[ref]

    @Command(__help__=N_("Set property for object on stack"))
    def setObjectProperty(self, ref, name, value):
        """
        Set a property on an existing stack object.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        ref               UUID / object reference
        name              Property name
        value             Property value
        ================= ==========================
        """
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
        """
        Get a property of an existing stack object.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        ref               UUID / object reference
        name              Property name
        ================= ==========================

        ``Return``: mixed
        """
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
        """
        Call a member method of the referenced object.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        ref               UUID / object reference
        method            Method name
        args              Arguments to pass to the method
        ================= ==========================

        ``Return``: mixed
        """
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
        """
        Open object on the agent side. This creates an instance on the
        stack and returns an a JSON description of the object and it's
        values.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        oid               OID of the object to create
        args/kwargs       Arguments to be used when getting an object instance
        ================= ==========================

        ``Return``: JSON encoded object description
        """
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
            propvals = dict([(p, getattr(obj, p)) for p in properties])

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
        if not oid in ObjectRegistry.objects:
            raise ValueError("Unknown object OID %s" % oid)
        return oid in ObjectRegistry.objects

    def __get_proxy(self, ref):
        return self.__get_proxy_by_oid(
                JSONRPCObjectMapper.__store[ref]['oid'])

    def __get_proxy_by_oid(self, oid):
        # Choose a possible node
        cr = PluginRegistry.getInstance('CommandRegistry')
        nodes = cr.get_load_sorted_nodes()
        provider = None

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
