# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: command.py 612 2010-08-16 09:21:44Z cajus $$

 This is the zeroconf provider module.

 See LICENSE for more information about the licensing.
"""
import re
import string
import inspect
from zope.interface import implements

from gosa.common.handler import IInterfaceHandler
from gosa.common.components import Command, CommandInvalid, CommandNotAuthorized
from gosa.common.components.registry import PluginRegistry
from gosa.common import Environment


class ClientCommandRegistry(object):
    implements(IInterfaceHandler)
    _priority_ = 2
    commands = {}
    nodes = {}
    proxy = {}

    def __init__(self):
        """
        Construct a new ClientCommandRegistry instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        env.log.debug("initializing command registry")
        self.env = env

        for clazz in PluginRegistry.modules.values():
            for method in clazz.__dict__.values():
                if hasattr(method, "isCommand"):

                    func = method.__name__
                    if not method.__doc__:
                        raise Exception("method '%s' has no documentation" % func)
                    doc = re.sub("(\s|\n)+" , " ", method.__doc__).strip()

                    env.log.debug("registering %s" % func)
                    info = {
                        'path': "%s.%s" % (clazz.__name__, method.__name__),
                        'sig': inspect.getargspec(method).args,
                        'doc': doc,
                        }
                    self.commands[func] = info

    def dispatch(self, func, *arg, **larg):
        """
        The dispatch method will try to call the specified function and
        checks for user and queue. Additionally, it carries the call to
        it's really destination (function types, cummulative results) and
        does some sanity checks.

        Handlers like JSONRPC or AMQP should use this function to
        dispatch the real calls.

        @type func: str
        @param func: the method name

        @type arg: var
        @param arg: list of function parameters

        @type larg: var
        @param larg: dict of named function parameters

        @rtype: var
        @return: the real methods result
        """

        # Do we have this method?
        if func in self.commands:
            (clazz, method) = self.path2method(self.commands[func]['path'])

            return PluginRegistry.modules[clazz].\
                    __getattribute__(method)(*arg, **larg)
        else:
            raise CommandInvalid("no method '%s' available" % func)

    def __del__(self):
        self.env.log.debug("shutting down command registry")

    @Command()
    def getMethods(self):
        """ List all available client commands """
        return self.commands

    def path2method(self, path):
        """
        Converts the call path (class.method) to the method itself

        @type path: str
        @param path: method path including the class

        @rtype: str
        @result: the method name
        """
        return string.rsplit(path, '.')
