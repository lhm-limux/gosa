# -*- coding: utf-8 -*-
"""
Overview
========

The *dbus* module bundles the dbus daemon and a couple code modules
needed to run it. The dbus itself is meant to be extended by plugins
using the :class:`gosa.common.components.plugin.Plugin` interface.
When starting up the system, the client looks for plugins in the setuptools
system and registers them into to the :class:`gosa.common.components.registry.PluginRegistry`.

After the *PluginRegistry* is ready with loading the modules, it orders
them by priority and loads them in sorted order.

The client is now in a state where it enters the main loop by sending
an AMQP ``ClientAnnounce`` event to be recognized by agents.

To provide services an ordinary client will load a couple of modules
exposing functionality to the outside world. Here are some of them:

 * :class:`gosa.client.command.CommandRegistry` inspects all loaded modules
   for the :meth:`gosa.common.components.command.Command` decorator
   and registers all decorated methods to be available thru the CommandRegistry
   dispatcher.

 * :class:`gosa.client.amqp_service.AMQPService` joins to the qpid broker
   federation and provides methods to *speak* with the bus.


This happens automatically depending on what's registered on the
``[gosa_dbus.modules]`` setuptools entrypoint.

The client will send a **ClientLeave** event when shutting down.

If you're looking for documentation on how to write plugins, please take a look
at the :ref:`Plugin section<plugins>`.
"""
__version__ = __import__('pkg_resources').get_distribution('gosa.dbus').version
__import__('pkg_resources').declare_namespace(__name__)
