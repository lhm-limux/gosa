"""
This code is part of GOsa (http://www.gosa-project.org)
Copyright (C) 2009, 2010 GONICUS GmbH

ID: $$Id: command.py 1360 2010-11-15 13:42:15Z cajus $$

This is the zeroconf provider module.

See LICENSE for more information about the licensing.
"""
import string
import sys
import time
import datetime
import re
from inspect import getargspec, getmembers, ismethod
from zope.interface import implements
from lxml import objectify

from gosa.common.components.registry import PluginRegistry
from gosa.common.components.command import Command
from gosa.common.handler import IInterfaceHandler
from gosa.common.env import Environment
from gosa.common.event import EventMaker
from gosa.common.utils import stripNs, N_
from gosa.common.components.amqp_proxy import AMQPServiceProxy
from gosa.common.components.amqp import EventConsumer


# Global command types
NORMAL = 1
FIRSTRESULT = 2
CUMULATIVE = 4


class CommandInvalid(Exception):
    """ Exception which is raised when the command is not valid. """
    pass


class CommandNotAuthorized(Exception):
    """ Exception which is raised when the call was not authorized. """
    pass


class CommandRegistry(object):
    """
    This class covers the registration and invocation of methods
    imported thru plugins. All methods marked with the @Command()
    decorator will be available.

    @type capabilites: dict
    @ivar capabilites: cluster capabilities

    @type commands: dict
    @ivar commands: local capabilities

    @type nodes: dict
    @ivar nodes: available nodes

    @type proxy: dict
    @ivar proxy: command proxies for queues
    """
    implements(IInterfaceHandler)

    # Target queue
    _target_ = 'core'

    capabilities = {}
    commands = {}
    nodes = {}
    proxy = {}

    def __init__(self):
        """
        Construct a new CommandRegistry instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        env.log.debug("initializing command registry")
        self.env = env

    @Command(__doc__=N_("List available service nodes on the bus."))
    def getNodes(self):
        return self.nodes

    @Command(needsQueue=False, __doc__=N_("List available methods "+
        "that are registered on the bus."))
    def getMethods(self, queue=None, locale=None):
        res = {}
        if queue == None:
            queue = self.env.domain + ".command.core"

        if queue == self.env.domain + ".command.core":
            node = None
        else:
            node = queue.split('.')[-1]

        #TODO: handle locale for __doc__
        for name, info in self.capabilities.iteritems():

            # Only list local methods
            if node:
                if node in info['provider']:
                    res[name] = info

            # List all available methods where we have
            # non dead providers in the list
            else:
                if self.isAvailable(info['provider']):
                    res[name] = info

        return res

    @Command(needsQueue=True, __doc__=N_("Shut down the service belonging to "+
        "the supplied queue. In case of HTTP connections, this command will shut"+
        " down the node you're currently logged in."))
    def shutdown(self, queue, force=False):
        if not force and queue == self.env.domain + '.command.core':
            return False

        self.env.log.debug("received shutdown signal - waiting for threads to terminate")
        self.env.active = False

    def isAvailable(self, providers):
        """
        Check if the list of providers contain at least one
        node which is available.

        @type providers: list
        @param providers: list of providers to be checked against current nodes

        @rtype: bool
        @return: flag if available or not
        """
        for provider in providers:
            if provider in self.nodes:
                return True
        return False

    def hasMethod(self, func):
        """
        Check if the desired method is available.

        @type func: str
        @param func: method to check for

        @rtype: bool
        @return: flag if available or not
        """
        return func in self.commands

    def call(self, func, *arg, **larg):
        return self.dispatch('internal', None, func, arg, larg)

    def dispatch(self, user, queue, func, *arg, **larg):
        """
        The dispatch method will try to call the specified function and
        checks for user and queue. Additionally, it carries the call to
        it's really destination (function types, cummulative results) and
        does some sanity checks.

        Handlers like JSONRPC or AMQP should use this function to
        dispatch the real calls.

        @type user: str
        @param user: the calling users name

        @type queue: str
        @param queue: the queue address where the call originated from

        @type func: str
        @param func: the method name

        @type arg: var
        @param arg: list of function parameters

        @type larg: var
        @param larg: dict of named function parameters

        @rtype: var
        @return: the real methods result
        """
        # Check for user authentication
        if not user:
            raise CommandNotAuthorized("call of function '%s' without a valid username is not permitted" % func)

        # Check if the command is available
        if not func in self.capabilities:
            raise CommandInvalid("no function '%s' defined" % func)

        # Depending on the call method, we may have no queue information
        if not queue:
            queue = self.env.domain + ".command.%s" % self.capabilities[func]['target']

        # Convert to list
        arg = list(arg)

        # Check if the command needs a special queue for beeing executed,
        # shutdown i.e. may not be very handy if globally executed.
        if self.callNeedsQueue(func):
            if not self.checkQueue(func, queue):
                raise CommandInvalid("invalid queue '%s' for function '%s'" % (queue, func))
            else:
                arg.insert(0, queue)

        # Check if call is interested in calling user ID, prepend it
        if self.callNeedsUser(func):
            arg.insert(0, user)

        # Handle function type (additive, first match, regular)
        methodType = self.capabilities[func]['type']

        # Type NORMAL, do a straight execute
        if methodType == NORMAL:

            # Do we have this method locally?
            if func in self.commands:
                (clazz, method) = self.path2method(self.commands[func]['path'])

                return PluginRegistry.modules[clazz].\
                        __getattribute__(method)(*arg, **larg)
            else:
                # Sort nodes by load, use first which is in [func][provider]
                nodes = sorted(self.nodes.items(), lambda x, y: cmp(x[1]['load'], y[1]['load']))

                # Get first match that is a provider for this function
                for provider, node in nodes:
                    if provider in self.capabilities[func]['provider']:
                        break

                # Set target queue directly to the evaulated node which provides that method
                target = self.env.domain + '.command.%s.%s' % (self.capabilities[func]['target'], provider)

                # Load amqp service proxy for that queue if not already present
                if not target in self.proxy:
                    amqp = PluginRegistry.getInstance("AMQPHandler")
                    self.proxy[target] = AMQPServiceProxy(amqp.url['source'], target)

                # Run the query
                methodCall = getattr(self.proxy[target], method)
                return methodCall(*arg, **larg)

        # FIRSTRESULT: try all providers, return on first non exception
        # CUMMULATIVE: try all providers, merge non exception results
        elif methodType == FIRSTRESULT or methodType == CUMULATIVE:
            # Walk thru nodes
            result = None
            for node, props in self.nodes.iteritems():

                # Don't bother with non provider nodes, just skip them
                if not node in self.capabilities[func]['provider']:
                    continue

                # Is it me?
                if node == self.env.id:
                    (clazz, method) = self.path2method(self.commands[func]['path'])
                    methodCall = PluginRegistry.modules[clazz].__getattribute__(method)
                else:
                    # Set target queue directly to the evaulated node which provides that method
                    target = self.env.domain + '.command.%s.%s' % (self.capabilities[func]['target'], node)

                    # Load amqp service proxy for that queue if not already present
                    if not target in self.proxy:
                        amqp = PluginRegistry.getInstance("AMQPHandler")
                        self.proxy[target] = AMQPServiceProxy(amqp.url['source'], target)

                    methodCall = getattr(self.proxy[target], method)

                # Finally do the call
                try:
                    tmp = methodCall(*arg, **larg)

                    if methodType == FIRSTRESULT:
                        return tmp
                    else:
                        if result == None:
                            result = {}

                        result[node] = tmp
                except:
                    # We do not care, go to the next entry...
                    pass

            return result

        else:
            raise CommandInvalid("no method type '%s' defined" % methodType)

    def path2method(self, path):
        """
        Converts the call path (class.method) to the method itself

        @type path: str
        @param path: method path including the class

        @rtype: str
        @result: the method name
        """
        return string.rsplit(path, '.')

    def callNeedsUser(self, func):
        """
        Checks if the provided method requires a user parameter.

        @type func: str
        @param func: method name

        @rtype: bool
        @result: success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])

        method = PluginRegistry.modules[clazz].__getattribute__(method)
        return getattr(method, "needsUser", False)

    def callNeedsQueue(self, func):
        """
        Checks if the provided method requires a queue parameter.

        @type func: str
        @param func: method name

        @rtype: bool
        @result: success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])

        method = PluginRegistry.modules[clazz].__getattribute__(method)
        return getattr(method, "needsQueue", False)

    def checkQueue(self, func, queue):
        """
        Checks if the provided method was sent to the correct queue.

        @type func: str
        @param func: method name

        @type queue: str
        @param queue: queue to compare to

        @rtype: bool
        @result: success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])
        p = re.compile(r'\.' + self.env.id + '$')
        p.sub('', queue)
        return self.env.domain + '.command.%s' % PluginRegistry.modules[clazz].__getattribute__('_target_') == p.sub('', queue)

    def __del__(self):
        self.env.log.debug("shutting down command registry")

    def __eventProcessor(self, data):
        eventType = stripNs(data.xpath('/g:Event/*', namespaces={'g': "http://www.gonicus.de/Events"})[0].tag)
        func = getattr(self, "_handle" + eventType)
        func(data)

    def _handleNodeAnnounce(self, data):
        data = data.NodeAnnounce
        self.env.log.debug("received hello of node %s" % data.Id)

        # Reply with sending capabilities
        amqp = PluginRegistry.getInstance("AMQPHandler")

        # Send capabilities
        e = EventMaker()
        methods = []
        for command in self.commands:
            info = self.commands[command]
            mtype = {1: 'NORMAL', 2: 'FIRSTRESULT', 3: 'CUMMULATIVE'}[info['type']]
            methods.append(
                e.NodeMethod(
                    e.Name(command),
                    e.Path(info['path']),
                    e.Target(info['target']),
                    e.Signature(','.join(info['sig'])),
                    e.Type(mtype),
                    e.QueueRequired('true' if info['needsQueue'] else 'false'),
                    e.Documentation(info['doc'])))
        caps = e.Event(
            e.NodeCapabilities(
                e.Id(self.env.id),
                *methods))
        amqp.sendEvent(caps)

    def _handleNodeCapabilities(self, data):
        data = data.NodeCapabilities
        self.env.log.debug("received capabilities of node %s" % data.Id)

        # Add methods
        for method in data.NodeMethod:
            methodName = method.Name.text
            if not methodName in self.capabilities:
                mtype = {'NORMAL': 1, 'FIRSTRESULT': 2, 'CUMMULATIVE': 3}
                self.capabilities[methodName] = {
                    'path': method.Path.text,
                    'target': method.Target.text,
                    'sig': string.split(method.Signature.text, ','),
                    'type': mtype[method.Type.text],
                    'needsQueue': method.QueueRequired.text == "true",
                    'doc': method.Documentation.text}
                self.capabilities[methodName]['provider'] = []

            # Append the sender as a new provider
            self.capabilities[methodName]['provider'].append(data.Id.text)

    def _handleNodeStatus(self, data):
        data = data.NodeStatus
        self.env.log.debug("received status of node %s" % data.Id)

        # Add recieve time to be able to sort out dead nodes
        t = datetime.datetime.utcnow()
        self.nodes[data.Id.text] = {
            'load': float(data.Load),
            'latency': float(data.Latency),
            'workers': int(data.Workers),
            'received': time.mktime(t.timetuple())}

    def _handleNodeLeave(self, data):
        """ Receive goodbye messages and act accordingly. """
        data = data.NodeLeave
        sender = data.Id.text
        self.env.log.debug("received goodbye of node %s" % sender)

        # Remove node from nodes
        if sender in self.nodes:
            del self.nodes[sender]

        # Remove node from capabilites
        capabilities = {}
        for name, info in self.capabilities.iteritems():
            if sender in info['provider']:
                info['provider'].remove(sender)
            if len(info['provider']):
                self.capabilities[name] = info
        self.capabilities = capabilities

    def updateNodes(self):
        """
        Maintain node list. Remove entries that haven't shown up
        in the configured interval.
        """
        nodes = {}
        timeout = self.env.config.getOption('node-timeout', 'core', 60)

        for node, info in self.nodes.iteritems():
            t = datetime.datetime.utcnow()
            if time.mktime(t.timetuple()) - info['received'] < timeout:
                nodes[node] = info

        self.nodes = nodes

    def serve(self):
        """
        Start serving the command registry to the outside world. Send
        hello and register event callbacks.
        """
        amqp = PluginRegistry.getInstance("AMQPHandler")

        for name, clazz in PluginRegistry.modules.iteritems():
            for mname, method in getmembers(clazz):
                if ismethod(method) and hasattr(method, "isCommand"):

                    func = mname
                    if not method.__doc__:
                        raise Exception("method '%s' has no documentation" % func)

                    doc = re.sub("(\s|\n)+", " ", method.__doc__).strip()

                    self.env.log.debug("registering %s" % func)
                    info = {
                        'name': func,
                        'path': "%s.%s" % (clazz.__class__.__name__, mname),
                        'target': clazz._target_,
                        #TODO: Check why this does not work with keyword arg only functions
                        'sig': 'unknown' if not getargspec(method).args else getargspec(method).args,
                        'type': getattr(method, "type", NORMAL),
                        'needsQueue': getattr(method, "needsQueue", False),
                        'doc': doc,
                        }
                    self.commands[func] = info


        # Add event processor
        EventConsumer(self.env,
            amqp.getConnection(),
            xquery="""
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:NodeAnnounce
                    or $e/f:NodeLeave
                    or $e/f:NodeCapabilities
                    or $e/f:NodeStatus
            """,
            callback=self.__eventProcessor)

        # Announce ourselves
        e = EventMaker()
        announce = e.Event(e.NodeAnnounce(e.Id(self.env.id)))
        amqp.sendEvent(announce)

    @Command(__doc__=N_("Send event to the bus."))
    def sendEvent(self, data):
        #TODO: check for permission
        amqp = PluginRegistry.getInstance("AMQPHandler")
        amqp.sendEvent(data)
