# -*- coding: utf-8 -*-
"""
The *CommandRegistry* is responsible for knowing what kind of commands
are available for users. It works together with the
:class:`gosa.common.components.registry.PluginRegistry` and inspects
all loaded plugins for methods marked with the
:meth:`gosa.common.components.command.Command` decorator. All available
information like *method path*, *command name*, *target queue*,
*documentation* and *signature* are recorded and are available for users
via the :meth:`gosa.agent.command.CommandRegistry.dispatch` method
(or better with the several proxies) and the CLI.

Next to registering commands, the *CommandRegistry* is also responsible
for sending and receiving a couple of important bus events:

================= ==========================
Name              Direction
================= ==========================
NodeCapabilities  send/receive
NodeAnnounce      send/receive
NodeLeave         receive
NodeStatus        receive
================= ==========================

All mentioned signals maintain an internal list of available nodes,
their status and their capabilities - aka collection of supported
methods and their signatures. This information is used to locate a
willing node for methods that the receiving node is not able to
process.

-------
"""
import string
import time
import datetime
import re
from inspect import getargspec, getmembers, ismethod
from zope.interface import implements
from gosa.common.components import PluginRegistry, ObjectRegistry, Command
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.common.event import EventMaker
from gosa.common.utils import stripNs, N_
from gosa.common.components import AMQPServiceProxy
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
    imported thru plugins.
    """
    implements(IInterfaceHandler)
    _priority_ = 0

    # Target queue
    _target_ = 'core'

    capabilities = {}
    objects = {}
    commands = {}
    nodes = {}
    proxy = {}

    def __init__(self):
        env = Environment.getInstance()
        env.log.debug("initializing command registry")
        self.env = env

    @Command(__help__=N_("List available service nodes on the bus."))
    def getNodes(self):
        """
        Returns a list of available nodes.

        ``Return``: list of nodes
        """
        return self.nodes

    @Command(needsQueue=False, __help__=N_("List available methods "+
        "that are registered on the bus."))
    def getMethods(self, queue=None, locale=None):
        """
        Lists the all methods that are available in the domain.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        queue             Ask for methods on special queue, None for all
        locale            Translate __help__ strings to the desired language
        ================= ==========================

        ``Return``: dict describing all methods
        """
        res = {}
        if queue == None:
            queue = self.env.domain + ".command.core"

        if queue == self.env.domain + ".command.core":
            node = None
        else:
            node = queue.split('.')[-1]

        #TODO: handle locale for __help__
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

    @Command(needsQueue=True, __help__=N_("Shut down the service belonging to "+
        "the supplied queue. In case of HTTP connections, this command will shut"+
        " down the node you're currently logged in."))
    def shutdown(self, queue, force=False):
        """
        Shut down the service belonging to the supplied queue. In case of HTTP
        connections, this command will shut down the node you're currently
        logged in.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        force             force global shut down
        ================= ==========================

        ``Return``: True when shutting down
        """
        if not force and queue == self.env.domain + '.command.core':
            return False

        self.env.log.debug("received shutdown signal - waiting for threads to terminate")
        self.env.active = False
        return True

    def isAvailable(self, providers):
        """
        Check if the list of providers contain at least one
        node which is available.

        ========== ============
        Parameter  Description
        ========== ============
        providers  list of providers
        ========== ============

        ``Return:`` bool flag if at least one available or not
        """
        for provider in providers:
            if provider in self.nodes:
                return True
        return False

    def hasMethod(self, func):
        """
        Check if the desired method is available.

        ========== ============
        Parameter  Description
        ========== ============
        func       method to check for
        ========== ============

        ``Return:`` flag if available or not
        """
        return func in self.commands

    def call(self, func, *arg, **larg):
        """
        *call* can be used to internally call a registered method
        directly. There's no access control happening with this
        method.

        ========== ============
        Parameter  Description
        ========== ============
        func       method to call
        args       ordinary argument list/dict
        ========== ============

        ``Return:`` return value from the method call
        """
        return self.dispatch('internal', None, func, arg, larg)

    def dispatch(self, user, queue, func, *arg, **larg):
        """
        The dispatch method will try to call the specified function and
        checks for user and queue. Additionally, it carries the call to
        it's really destination (function types, cummulative results) and
        does some sanity checks.

        Handlers like JSONRPC or AMQP should use this function to
        dispatch the real calls.

        ========== ============
        Parameter  Description
        ========== ============
        user       the calling users name
        queue      the queue address where the call originated from
        func       method to call
        args       ordinary argument list/dict
        ========== ============

        Dispatch will...

          * ... forward *unknown* commands to nodes that
            are capable of processing them - ordered by load.

          * ... will take care about the modes *NORMAL*, *FIRSTRESULT*,
            *CUMULATIVE* like defined in the *Command* decorator.

        ``Return:`` the real methods result
        """

        #TODO: check for permission

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
                nodes = self.get_load_sorted_nodes()

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
            for node in self.nodes.keys():

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

        ========== ============
        Parameter  Description
        ========== ============
        path       method path including the class
        ========== ============

        ``Return:`` the method name
        """
        return string.rsplit(path, '.')

    def callNeedsUser(self, func):
        """
        Checks if the provided method requires a user parameter.

        ========== ============
        Parameter  Description
        ========== ============
        func       method name
        ========== ============

        ``Return:`` success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])

        method = PluginRegistry.modules[clazz].__getattribute__(method)
        return getattr(method, "needsUser", False)

    def callNeedsQueue(self, func):
        """
        Checks if the provided method requires a queue parameter.

        ========== ============
        Parameter  Description
        ========== ============
        func       method name
        ========== ============

        ``Return:`` success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])

        method = PluginRegistry.modules[clazz].__getattribute__(method)
        return getattr(method, "needsQueue", False)

    def checkQueue(self, func, queue):
        """
        Checks if the provided method was sent to the correct queue.

        ========== ============
        Parameter  Description
        ========== ============
        func       method name
        queue      queue to compare to
        ========== ============

        ``Return:`` success or failure
        """
        if not func in self.commands:
            raise CommandInvalid("no function '%s' defined" % func)

        (clazz, method) = self.path2method(self.commands[func]['path'])
        p = re.compile(r'\.' + self.env.id + '$')
        p.sub('', queue)
        return self.env.domain + '.command.%s' % PluginRegistry.modules[clazz].__getattribute__('_target_') == p.sub('', queue)

    def get_load_sorted_nodes(self):
        """
        Return a node list sorted by node *load*.

        ``Return:`` list
        """
        return sorted(self.nodes.items(), lambda x, y: cmp(x[1]['load'], y[1]['load']))

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

        for obj, info in ObjectRegistry._objects.iteritems():
            if info['signature']:
                methods.append(
                    e.NodeObject(
                        e.OID(obj),
                        e.Signature(info['signature'])))
            else:
                methods.append(e.NodeObject(e.OID(obj)))

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

        # Add objects
        if hasattr(data, 'NodeObject'):
            for obj in data.NodeObject:
                oid = obj.OID.text
                if not oid in self.objects:
                    self.objects[oid] = []

                # Append the sender as a new provider
                self.objects[oid].append(data.Id.text)

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
        timeout = self.env.config.get('core.node-timeout', 60)

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

        for clazz in PluginRegistry.modules.values():
            for mname, method in getmembers(clazz):
                if ismethod(method) and hasattr(method, "isCommand"):
                    func = mname

                    # Adjust documentation
                    if not method.__help__:
                        raise Exception("method '%s' has no documentation" % func)
                    doc = re.sub("(\s|\n)+", " ", method.__help__).strip()

                    self.env.log.debug("registering %s" % func)
                    info = {
                        'name': func,
                        'path': "%s.%s" % (clazz.__class__.__name__, mname),
                        'target': clazz._target_,
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

    @Command(__help__=N_("Send event to the bus."))
    def sendEvent(self, data):
        """
        Sends an event to the AMQP bus. Data must be in XML format,
        see :ref:`Events handling <events>` for details.

        ========== ============
        Parameter  Description
        ========== ============
        data       valid event
        ========== ============

        *sendEvent* will indirectly validate the event against the bundeled "XSD".
        """
        #TODO: check for permission
        amqp = PluginRegistry.getInstance("AMQPHandler")
        amqp.sendEvent(data)
