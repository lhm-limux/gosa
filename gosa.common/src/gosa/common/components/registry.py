# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: registry.py 608 2010-08-16 08:12:35Z cajus $$

 This modules hosts plugin registry related classes.

 See LICENSE for more information about the licensing.
"""
import pkg_resources

from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment


class PluginRegistry(object):
    """
    Plugin registry class. The registry holds plugin instances and
    provides overall functionality like "serve" and "shutdown".
    """
    modules = {}
    handlers = {}
    objects = {}

    def __init__(self, component="gosa.modules"):
        """
        Construct a new message with the supplied content. The
        content-type of the message will be automatically inferred from
        type of the content parameter.

        @type env: Environment
        @param env: L{Environment} object

        @type component: string
        @param component: Which entrypoints should be include
        """
        env = Environment.getInstance()
        self.env = env
        self.env.log.debug("inizializing plugin registry")

        # Get module from setuptools
        for entry in pkg_resources.iter_entry_points(component):
            module = entry.load()
            self.env.log.info("module %s included" % module.__name__)
            PluginRegistry.modules[module.__name__] = module

            # Save interface handlers
            # pylint: disable-msg=E1101
            if IInterfaceHandler.implementedBy(module):
                self.env.log.debug("registering handler module %s" % module.__name__)
                PluginRegistry.handlers[module.__name__] = module

        # Initialize component handlers
        for handler, clazz  in PluginRegistry.handlers.iteritems():
            PluginRegistry.handlers[handler] = clazz()

        # Initialize modules
        for module, clazz  in PluginRegistry.modules.iteritems():
            if module in PluginRegistry.handlers:
                PluginRegistry.modules[module] = PluginRegistry.handlers[module]
            else:
                PluginRegistry.modules[module] = clazz()

        # Let handlers serve
        for handler, clazz in sorted(PluginRegistry.handlers.iteritems(),
                key=lambda k: k[1]._priority_):

            if hasattr(clazz, 'serve'):
                clazz.serve()

        #NOTE: For component handler: list implemented interfaces
        #print(list(zope.interface.implementedBy(module)))

    @staticmethod
    def shutdown():
        """
        Call handlers stop() methods in order to grant a clean shutdown.
        """
        for clazz  in PluginRegistry.handlers.values():
            if hasattr(clazz, 'stop'):
                clazz.stop()

    @staticmethod
    def registerObject(oid, obj):
        if oid in  PluginRegistry.objects:
            raise ValueError("OID '%s' is already registerd!" % oid)

        PluginRegistry.objects[oid] = {
            'object': obj,
            'signature': None}

    @staticmethod
    def getInstance(name):
        """
        Return an instance of the named class.

        @type name: str
        @param name: name of the class to get instance of
        """
        if not name in PluginRegistry.modules:
            raise ValueError("no module '%s' available" % name)

        return PluginRegistry.modules[name]
