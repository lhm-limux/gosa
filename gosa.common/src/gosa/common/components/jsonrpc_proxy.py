# -*- coding: utf-8 -*-
import urllib2
import cookielib
from types import DictType
from jsonrpc.json import dumps, loads


class JSONRPCException(Exception):
    """
    Exception raises if there's an error when processing JSONRPC related
    tasks.
    """
    def __init__(self, rpcError):
        super(JSONRPCException, self).__init__(rpcError)
        self.error = rpcError


class ObjectFactory(object):

    def __init__(self, proxy, ref, oid, methods, properties, data):
        object.__setattr__(self, "proxy", proxy)
        object.__setattr__(self, "ref", ref)
        object.__setattr__(self, "oid", oid)
        object.__setattr__(self, "methods", methods)
        object.__setattr__(self, "properties", properties)

        for prop in properties:
            object.__setattr__(self, "_" + prop, None if not prop in data else data[prop])

    def _call(self, name, *args):
        ref = object.__getattribute__(self, "ref")
        return object.__getattribute__(self, "proxy").dispatchObjectMethod(ref, name, *args)

    def __getattribute__(self, name):
        if name in object.__getattribute__(self, "methods"):
            return lambda *f: object.__getattribute__(self, "_call")(*[name] + list(f))

        if not name in object.__getattribute__(self, "properties"):
            raise AttributeError("'%s' object has no attribute '%s'" %
                (type(self).__name__, name))

        return object.__getattribute__(self, "_" + name)

    def __setattr__(self, name, value):
        if not name in object.__getattribute__(self, "properties"):
            raise AttributeError("'%s' object has no attribute '%s'" %
                (type(self).__name__, name))

        ref = object.__getattribute__(self, "ref")
        object.__getattribute__(self, "proxy").setObjectProperty(ref, name, value)
        object.__setattr__(self, "_" + name, value)

    def __repr__(self):
        return object.__getattribute__(self, "ref")

    @staticmethod
    def get_instance(proxy, obj_type, ref, oid, methods, properties, data=None):
        return type(str(obj_type),
                (ObjectFactory, object),
                ObjectFactory.__dict__.copy())(proxy, ref, oid, methods, properties, data)


class JSONServiceProxy(object):
    """
    The JSONServiceProxy provides a simple way to use GOsa RPC
    services from various clients. Using the proxy object, you
    can directly call methods without the need to know where
    it actually gets executed.

    Example::

        >>> proxy = JSONServiceProxy('https://localhost')
        >>> proxy.login("admin", "secret")
        >>> proxy.getMethods()
        ...
        >>> proxy.logout()

    This will return a dictionary describing the available methods.

    =============== ============
    Parameter       Description
    =============== ============
    serviceURL      URL used to connect to the HTTP service
    serviceName     *internal*
    opener          *internal*
    =============== ============

    The URL format is::

       (http|https)://user:password@host:port/rpc

    .. note::
       The HTTP service is operated by a gosa-agent instance. This means
       that you don't have load balancing and failover out of the box.
       If you need these features, you should use :class:`gosa.common.components.amqp_proxy.AMQPServiceProxy`
       instead.
    """

    def __init__(self, serviceURL=None, serviceName=None, opener=None):
        self.__serviceURL = serviceURL
        self.__serviceName = serviceName

        if not opener:
            http_handler = urllib2.HTTPHandler()
            https_handler = urllib2.HTTPSHandler()
            cookie_handler = urllib2.HTTPCookieProcessor(cookielib.CookieJar())
            opener = urllib2.build_opener(http_handler, https_handler, cookie_handler)

        self.__opener = opener

    def __getattr__(self, name):
        if self.__serviceName != None:
            name = "%s.%s" % (self.__serviceName, name)

        return JSONServiceProxy(self.__serviceURL, name, self.__opener)

    def __call__(self, *args):
        postdata = dumps({"method": self.__serviceName, 'params': args, 'id': 'jsonrpc'})
        respdata = self.__opener.open(self.__serviceURL, postdata).read()
        resp = loads(respdata)
        if resp['error'] != None:
            raise JSONRPCException(resp['error'])
        else:
            # Look for json class hint
            if "result" in resp and \
                isinstance(resp["result"], DictType) and \
                "__jsonclass__" in resp["result"] and \
                resp["result"]["__jsonclass__"][0] == "json.ObjectFactory":

                resp = resp["result"]
                jc = resp["__jsonclass__"][1]
                del resp["__jsonclass__"]

                # Extract property presets
                data = {}
                for prop in resp:
                    data[prop] = resp[prop]

                jc.insert(0, JSONServiceProxy(self.__serviceURL, None, self.__opener))
                jc.append(data)
                return ObjectFactory.get_instance(*jc)

            return resp['result']
