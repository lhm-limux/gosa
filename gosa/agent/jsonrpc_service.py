# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: jsonrpc_service.py 1267 2010-10-22 12:37:59Z cajus $$

 This modules hosts JSON related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import traceback
import thread
import uuid
from types import MethodType
from zope.interface import implements
from jsonrpc import loads, dumps
from webob import exc, Request, Response
from paste import httpserver, wsgilib, request, response
from paste.auth.cookie import AuthCookieHandler, AuthCookieSigner

from gosa.common.utils import N_, repr2json, f_print
from gosa.common.handler import IInterfaceHandler
from gosa.common.env import Environment
from gosa.common.components.jsonrpc_proxy import JSONRPCException
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.zeroconf import ZeroconfService
from gosa.common.components.command import Command
from gosa.common.components.amqp_proxy import AMQPServiceProxy


class JsonRpcApp(object):
    """ WSGI JSON service """

    # Simple authentication saver
    __session = {}

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.env = Environment.getInstance()

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(req, environ)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def process(self, req, environ):
        if not req.method == 'POST':
            raise exc.HTTPMethodNotAllowed(
                "Only POST allowed",
                allow='POST').exception
        try:
            json = loads(req.body)
        except ValueError, e:
            raise ValueError('Bad JSON: %s' % e)
        try:
            method = json['method']
            params = json['params']
            id = json['id']
        except KeyError, e:
            raise ValueError(
                "JSON body missing parameter: %s" % e)
        if method.startswith('_'):
            raise exc.HTTPForbidden(
                "Bad method name %s: must not start with _" % method).exception
        if not isinstance(params, list):
            raise ValueError(
                "Bad params %r: must be a list" % params)

        # Create an authentication cookie on login
        if method == 'login':
            (user, password) = params

            # Check password and create session id on success
            if self.authenticate(user, password):
                sid = str(uuid.uuid1())
                self.__session[sid] = user
                environ['REMOTE_USER'] = user
                environ['REMOTE_SESSION'] = sid
                result = True
                self.env.log.info("login succeeded for user '%s'" % user)
            else:
                # Remove current sid if present
                if 'REMOTE_SESSION' in environ and sid in self.__session:
                    del self.__session[sid]

                result = False
                self.env.log.error("login failed for user '%s'" % user)
                raise exc.HTTPUnauthorized(
                    "Login failed",
                    allow='POST').exception

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=result,
                                error=None,
                                id=id)))

        # Don't let calls pass beyond this point if we've no valid session ID
        if not environ.get('REMOTE_SESSION') in self.__session:
            self.env.log.error("blocked unauthenticated call of method '%s'" % method)
            raise exc.HTTPUnauthorized(
                    "Please use the login method to authorize yourself.",
                    allow='POST').exception

        # Remove remote session on logout
        if method == 'logout':

            # Remove current sid if present
            if 'REMOTE_SESSION' in environ and environ.get('REMOTE_SESSION') in self.__session:
                del self.__session[environ.get('REMOTE_SESSION')]

            # Show logout message
            if 'REMOTE_USER' in environ:
                self.env.log.info("logout for user '%s' succeeded" % environ.get('REMOTE_USER'))

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=True,
                                error=None,
                                id=id)))

        # Try to call method with local dispatcher
        if not self.dispatcher.hasMethod(method):
            text = "No such method '%s'" % method
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=text,
                error=text)
            self.env.log.warning(text)

            return Response(
                status=500,
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))
        try:
            self.env.log.debug("calling method %s(%s)" % (method, params))
            user = environ.get('REMOTE_USER')

            # Automatically prepend queue option for current
            if self.dispatcher.capabilities[method]['needsQueue']:
                queue= '%s.command.%s.%s' % (self.env.domain,
                    self.dispatcher.capabilities[method]['target'],
                    self.env.id)
                params.insert(0, queue)

            result = self.dispatcher.dispatch(user, None, method, *params)

        except JSONRPCException as e:
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=e.error)
            self.env.log.error(e.error)
            return Response(
                status=500,
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))
        except Exception as e:
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            err = str(e)

            # If message starts with [, it's a translateable message in
            # repr format
            if err.startswith("["):
                err = loads(repr2json(err))
            if err.startswith("("):
                err = "[" + err[1:-1] + "]"
                err = loads(repr2json(err))

            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=err)

            self.env.log.error("returning call [%s]: %s / %s" % (id, None, f_print(err)))
            self.env.log.error(text)

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))

        self.env.log.debug("returning call [%s]: %s / %s" % (id, result,
            None))

        return Response(
            content_type='application/json',
            charset='utf8',
            body=dumps(dict(result=result,
                            error=None,
                            id=id)))

    def authenticate(self, user=None, password=None):
        amqp = PluginRegistry.getInstance('AMQPHandler')
        return amqp.checkAuth(user, password)


class JSONRPCService(object):
    """ GOsa JSON-RPC provider """
    implements(IInterfaceHandler)

    __proxy = {}

    def __init__(self):
        env = Environment.getInstance()
        env.log.debug("initializing JSON RPC service provider")
        self.env = env
        self.path = self.env.config.getOption('path', 'jsonrpc', default="/rpc")

    def serve(self):
        # Get http service instance
        self.__http = PluginRegistry.getInstance('HTTPService')
        cr = PluginRegistry.getInstance('CommandRegistry')

        # Register ourselves
        app = JsonRpcApp(cr)
        self.__http.app.register(self.path, AuthCookieHandler(app,
            timeout=self.env.config.getOption('cookie-lifetime',
            'jsonrpc',
            default=1800), cookie_name='GOsaRPC'))

        # Announce service
        url= "%s://%s:%s%s" % (self.__http.scheme, self.__http.host, self.__http.port, self.path)
        self.__zeroconf = ZeroconfService(name="GOsa JSONRPC command service",
            port=self.__http.port,
            stype="_gosa._tcp",
            text=url)
        self.__zeroconf.publish()

    def stop(self):
        self.env.log.debug("shutting down JSON RPC service provider")
        self.__http.app.unregister(self.path)


class JSONRPCObjectMapper(object):
    _target_ = 'core'

    #TODO: move store to memcache or DB in order to allow shared
    #      objects accross agent instances
    __store = {}
    __proxy = {}

    @Command(__doc__=N_("Close object and remove it from stack"))
    def closeObject(self, ref):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)

        del JSONRPCObjectMapper.__store[ref]

    @Command(__doc__=N_("Set property for object on stack"))
    def setObjectProperty(self, ref, name, value):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not name in JSONRPCObjectMapper.__store[ref]['properties']:
            raise ValueError("property %s not found" % name)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.setObjectProperty(ref, name, value)

        return setattr(JSONRPCObjectMapper.__store[ref]['object'], name, value)

    @Command(__doc__=N_("Get property from object on stack"))
    def getObjectProperty(self, ref, name):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not name in JSONRPCObjectMapper.__store[ref]['properties']:
            raise ValueError("property %s not found" % name)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.getObjectProperty(ref, name)

        return getattr(JSONRPCObjectMapper.__store[ref]['object'], name)

    @Command(__doc__=N_("Call method from object on stack"))
    def dispatchObjectMethod(self, ref, method, *args):
        if not ref in JSONRPCObjectMapper.__store:
            raise ValueError("reference %s not found" % ref)
        if not method in JSONRPCObjectMapper.__store[ref]['methods']:
            raise ValueError("method %s not found" % name)

        if not self.__can_be_handled_locally(ref):
            proxy = self.__get_proxy(ref)
            return proxy.dispatchObjectMethod(ref, method, *args)

        return getattr(JSONRPCObjectMapper.__store[ref]['object'], method)(*args)

    @Command(__doc__=N_("Instantiate object and place it on stack"))
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
        if not oid in PluginRegistry.objects:
            raise ValueError("Unknown object OID %s" % oid)

        return PluginRegistry.objects[oid]['object']

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
        return oid in PluginRegistry.objects

    def __get_proxy(self, ref):
        return self.__get_proxy_by_oid(
                JSONRPCObjectMapper.__store[ref]['oid'])

    def __get_proxy_by_oid(self, oid):
        # Choose a possible node
        cr = PluginRegistry.getInstance('CommandRegistry')
        nodes = cr.get_load_sorted_nodes()

        # Get first match that is a provider for this object
        for provider, node in nodes:
            if provider in cr.objects[oid]:
                break

        if not provider in self.__proxy:
            env = Environment.getInstance()
            queue = '%s.core.%s' % (env.domain, provider)
            amqp = PluginRegistry.getInstance("AMQPHandler")
            self.__proxy[provider] = AMQPServiceProxy(amqp.url['source'], queue)

        return self.__proxy[provider]
