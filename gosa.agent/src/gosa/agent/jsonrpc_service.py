# -*- coding: utf-8 -*-
"""
The JSONRPC implementation consists of a GOsa agent plugin (*JSONRPCService*)
and a WSGI application (*JsonRpcApp*). The first is implemented as a handler
plugin, so it is going to be invoked on agent startup. It takes care of
registering the WSGI application to the
:class:`gosa.agent.httpd.HTTPService`.

------
"""
import sys
import uuid
import traceback
import logging
from zope.interface import implements
from gosa.common.json import loads, dumps
from webob import exc, Request, Response
from paste.auth.cookie import AuthCookieHandler
from gosa.common.utils import repr2json, f_print
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.common.components import PluginRegistry, ZeroconfService, JSONRPCException


class JSONRPCService(object):
    """
    This is the JSONRPC GOsa agent plugin which is registering an
    instance of :class:`gosa.agent.jsonrpc_service.JsonRpcApp` into the
    :class:`gosa.agent.httpd.HTTPService`.

    It is configured thru the ``[jsonrpc]`` section of your GOsa
    configuration:

    =============== ============
    Key             Description
    =============== ============
    path            Path to register the service in HTTP
    cookie-lifetime Seconds of authentication cookie lifetime
    =============== ============

    Example::

        [jsonrpc]
        path = /rpc
        cookie-lifetime = 3600
    """
    implements(IInterfaceHandler)
    _priority_ = 11

    __proxy = {}

    def __init__(self):
        env = Environment.getInstance()
        self.env = env
        self.log = logging.getLogger(__name__)
        self.log.debug("initializing JSON RPC service provider")
        self.path = self.env.config.get('jsonrpc.path', default="/rpc")

        self.__zeroconf = None
        self.__http = None

    def serve(self):
        """ Start JSONRPC service for this GOsa service provider. """

        # Get http service instance
        self.__http = PluginRegistry.getInstance('HTTPService')
        cr = PluginRegistry.getInstance('CommandRegistry')

        # Register ourselves
        app = JsonRpcApp(cr)
        self.__http.app.register(self.path, AuthCookieHandler(app,
            timeout=self.env.config.get('jsonrpc.cookie-lifetime',
            default=1800), cookie_name='GOsaRPC',
            secret=self.env.config.get('http.cookie_secret',
                default="TecloigJink4")))

        # Announce service
        self.__zeroconf = ZeroconfService(name="GOsa JSONRPC command service",
            port=self.__http.port,
            stype="_%s._tcp" % self.__http.scheme,
            text="path=%s\001service=gosa" % self.path)
        self.__zeroconf.publish()

        self.log.info("ready to process incoming requests")

    def stop(self):
        """ Stop serving the JSONRPC service for this GOsa service provider. """
        self.log.debug("shutting down JSON RPC service provider")
        self.__http.app.unregister(self.path)


class JsonRpcApp(object):
    """
    This is the WSGI application wich is responsible for serving the
    :class:`gosa.agent.command.CommandRegistry` via HTTP/JSONRPC.
    """

    # Simple authentication saver
    __session = {}

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)

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
        """
        Process an incoming JSONRPC request and dispatch it thru the
        *CommandRegistry*.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        req               Incoming Request
        environ           WSGI environment
        ================= ==========================

        ``Return``: varries
        """
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
            jid = json['id']
        except KeyError, e:
            raise ValueError(
                "JSON body missing parameter: %s" % e)
        if method.startswith('_'):
            raise exc.HTTPForbidden(
                "Bad method name %s: must not start with _" % method).exception
        if not isinstance(params, list) and not isinstance(params, dict):
            raise ValueError(
                "bad params %r: must be a list or dict" % params)

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
                self.log.info("login succeeded for user '%s'" % user)
            else:
                # Remove current sid if present
                if 'REMOTE_SESSION' in environ and sid in self.__session:
                    del self.__session[sid]

                result = False
                self.log.error("login failed for user '%s'" % user)
                raise exc.HTTPUnauthorized(
                    "Login failed",
                    allow='POST').exception

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=result,
                                error=None,
                                id=jid)))

        # Don't let calls pass beyond this point if we've no valid session ID
        if not environ.get('REMOTE_SESSION') in self.__session:
            self.log.error("blocked unauthenticated call of method '%s'" % method)
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
                self.log.info("logout for user '%s' succeeded" % environ.get('REMOTE_USER'))

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=True,
                                error=None,
                                id=jid)))

        # Try to call method with local dispatcher
        if not self.dispatcher.hasMethod(method):
            text = "No such method '%s'" % method
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=text,
                error=text)
            self.log.warning(text)

            return Response(
                status=500,
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=jid)))
        try:
            self.log.debug("calling method %s(%s)" % (method, params))
            user = environ.get('REMOTE_USER')

            # Automatically prepend queue option for current
            if self.dispatcher.capabilities[method]['needsQueue']:
                queue= '%s.command.%s.%s' % (self.env.domain,
                    self.dispatcher.capabilities[method]['target'],
                    self.env.id)
                if isinstance(params, dict):
                    params['queue'] = queue
                else:
                    params.insert(0, queue)

            self.log.info("received call [%s] for %s: %s(%s)" % (jid, user, method, params))

            # Don't process messages if the command registry thinks it's not ready
            if not self.dispatcher.processing.is_set():
                self.log.warning("waiting for registry to get ready")
                if not self.__cr.processing.wait(5):
                    self.log.error("aborting call [%s] for %s: %s(%s) - timed out" % (jid, user, method, params))
                    raise RuntimeError("registry not ready")

            if isinstance(params, dict):
                result = self.dispatcher.dispatch(user, None, method, **params)
            else:
                result = self.dispatcher.dispatch(user, None, method, *params)

        except JSONRPCException as e:
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=e.error)
            self.log.error(e.error)
            return Response(
                status=500,
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=jid)))
        except Exception as e:
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            err = str(e)

            # If message starts with [, it's a translateable message in
            # repr format
            if err.startswith("[") and not err.startswith("[Err"):
                err = loads(repr2json(err))
            if err.startswith("("):
                err = "[" + err[1:-1] + "]"
                err = loads(repr2json(err))

            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=err)

            self.log.error("returning call [%s]: %s / %s" % (jid, None, f_print(err)))
            self.log.error(text)

            return Response(
                content_type='application/json',
                charset='utf8',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=jid)))

        self.log.debug("returning call [%s]: %s / %s" % (jid, result, None))

        return Response(
            content_type='application/json',
            charset='utf8',
            body=dumps(dict(result=result,
                            error=None,
                            id=jid)))

    def authenticate(self, user=None, password=None):
        """
        Use the AMQP connection to authenticate the incoming HTTP request.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        user              User name to authenticate with
        password          Password
        ================= ==========================

        ``Return``: True on success
        """
        amqp = PluginRegistry.getInstance('AMQPHandler')
        return amqp.checkAuth(user, password)
