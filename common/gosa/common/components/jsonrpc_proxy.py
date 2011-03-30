# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (c) 2007 Jan-Klaas Kollhof
 Copyright (C) 2010 GONICUS GmbH

 ID: $$Id: jsonrpc_proxy.py 1238 2010-10-21 15:31:46Z cajus $$

 This file is part of jsonrpc. We have modified it to be able to
 use session based authentication.

 jsonrpc is free software; you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as published by
 the Free Software Foundation; either version 2.1 of the License, or
 (at your option) any later version.

 This software is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Lesser General Public License for more details.

 You should have received a copy of the GNU Lesser General Public License
 along with this software; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import os
import os.path
import urllib2
import cookielib
from types import DictType
from jsonrpc.json import dumps, loads


class JSONRPCException(Exception):
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
        return type(obj_type,
                (ObjectFactory, object),
                ObjectFactory.__dict__.copy())(proxy, ref, oid, methods, properties, data)


class JSONServiceProxy(object):
    """
    The JSONServiceProxy provides a simple way to use GOsa RPC
    services from various clients. Using the proxy object, you
    can directly call methods without the need to know where
    it actually gets executed.

    Example:

    proxy = JSONServiceProxy('https://localhost')
    print(proxy.login("admin", "secret"))
    print(proxy.getMethods())
    print(proxy.logout())

    This will list the available methods.
    """

    def __init__(self, serviceURL=None, serviceName=None, opener=None):
        """
        Instantiate the proxy object using the initializing parameters.

        @type serviceURL: string
        @param serviceURL: URL used to connect to the GOsa service
           http(s)://host:port
        """
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
                resp["result"]["__jsonclass__"][0] == "gosa.common.components.jsonrpc.ObjectFactory":

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
