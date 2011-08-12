# -*- coding: utf-8 -*-
"""
Overview
========

The *client* module bundles the client daemon and a couple code modules
needed to run it. The agent itself is meant to be extended by plugins
using the :class:`gosa.common.components.plugin.Plugin` interface.
When starting up the system, the agent looks for plugins in the setuptools
system and registers them into to the :class:`gosa.common.components.registry.PluginRegistry`.
The same happens for objects in :class:`gosa.common.components.objects.ObjectRegistry`.

After the *PluginRegistry* is ready with loading the modules, it orders
them by priority and tries to determine whether it is

 * an ordinary plugin
 * a dbus plugin

Modules marked with the *IInterfaceHandler* interface provide a *serve*
method which is instantly called in this case. Modules like i.e. a
AMQP handler or an HTTP service can start their own threads and
start processing what ever they need to process. When the service
shuts down, the method *stop* is called and the module has the chance
to cleanly shut down the process.

The agent is now in a state where it enters the main loop by sending
AMQP ``NodeStatus`` events from time to time, joining threads and waiting
to be stopped.

To provide real services an ordinary agent will load a couple of modules
exposing functionality to the outside world. Here are some of them:

 * :class:`gosa.client.command.CommandRegistry` inspects all loaded modules
   for the :meth:`gosa.common.components.command.Command` decorator
   and registers all decorated methods to be available thru the CommandRegistry
   dispatcher.

 * :class:`gosa.client.amqp_service.AMQPService` joins to the qpid broker
   federation and provides methods to *speak* with the bus.


This happens automatically depending on what's registered on the
``[gosa.modules]`` setuptools entrypoint.

If you're looking for documentation on how to write plugins, please take a look
at the :ref:`Plugin section<plugins>`.

Using the binary
================

The gosa-agent binary gets installed when you run the setup process. It
has a couple of command line arguments:

    .. program-output::  gosa-agent --help
       :prompt:

.. note::

   Take a look at the :ref:`quickstart <quickstart>` to see how the agent is
   controlled.

.. requirement::
   :status: todo

   Describe the init script / default usage

"""
__version__ = __import__('pkg_resources').get_distribution('gosa.client').version
__import__('pkg_resources').declare_namespace(__name__)
