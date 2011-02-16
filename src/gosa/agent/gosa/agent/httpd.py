# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: httpd.py 609 2010-08-16 08:19:05Z cajus $$

 This modules provides a simple HTTP service.

 See LICENSE for more information about the licensing.
"""
import sys
import traceback
import thread
from zope.interface import implements
from webob import exc, Request, Response
from paste import httpserver, wsgilib, request, response

from gosa.common.env import Environment
from gosa.common.handler import IInterfaceHandler
from gosa.common.components.registry import PluginRegistry


class HTTPDispatcher(object):

    def __init__(self):
        self.__app = {}

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO')
        if path in self.__app:
            return self.__app[path].__call__(environ, start_response)

        # Nothing found
        self.env.log.debug('no resource %s registered!' % path)
        resp = exc.HTTPNotFound('no resource %s registered!' % path)
        return resp(environ, start_response)

    def register(self, path, app):
        self.env.log.debug("registering %s on %s" % (app.__class__.__name__, path))
        self.__app[path] = app

    def unregister(self, path):
        if path in self.__app:
            self.env.log.debug("unregistering %s" % path)
            del(self.__app[path])


class HTTPService(object):

    implements(IInterfaceHandler)

    def __init__(self):
        env = Environment.getInstance()
        env.log.debug("initializing HTTP service provider")
        self.env = env

    def serve(self):
        # Start thread
        self.app = HTTPDispatcher()
        self.app.env = self.env
        self.host = self.env.config.getOption('host', 'http', default="localhost")
        self.port = self.env.config.getOption('port', 'http', default=8080)
        self.ssl_pem = self.env.config.getOption('sslpemfile', 'http', default=None)

        if self.ssl_pem:
            self.scheme = "https"
        else:
            self.scheme = "http"

        # Fetch server
        self.srv = httpserver.serve(self.app, self.host, self.port, start_loop=False, ssl_pem=self.ssl_pem)
        self.env.log.debug("serving http on %s://%s:%s" % (self.scheme, self.host, self.port))
        thread.start_new_thread(self.srv.serve_forever, ())

    def stop(self):
        self.env.log.debug("shutting down HTTP service provider")
        self.srv.server_close()
