# -*- coding: utf-8 -*-
"""
The *AMQPService* is responsible for connecting the *agent* to the AMQP
bus, registers the required queues, listens for commands on that queues
and dispatches incoming commands to the
:class:`gosa.agent.command.CommandRegistry`.

.. _agent-queues:

**Queues**

In order to use features like round robin and automatic routing of commands
to agents that are capable of handling them, the AMQPService creates a
queue structure that addresses these facts.

Queues are named after the configured *domain* - i.e. if you use the
configured default domain, you'll get ``org.gosa`` as the base dot
separated string for the queues. The agent registers two **core** queues:

 * **{domain}.command.core** *(i.e. org.gosa.command.core)*

   This is a round robin queue that is shared by all agents joining
   the domain. The core queue must only handle commands that are provided
   by all agents.

 * **{domain}.command.core.{nodename}** *(i.e. org.gosa.command.core.node1 if your node is named node1)*

   This queue is a private queue that is only used by a specific
   agent. It is possible to direct a command to exactly the agent identified
   by *nodename*.

The same thing which is established for the **command.core** queues is done
for queues registered by certain plugins. This ensures that commands are only
delivered to nodes which provide that functionality by listening to these
queues:

 * **{domain}.command.{plugin}** *(i.e. org.gosa.command.goto)*

   This is a round robin queue that is shared by all agents joining
   the domain. In the example above, all agents providing the *goto* plugin
   will share this queue.

 * **{domain}.command.{plugin}.nodename** *(i.e. org.gosa.command.goto.node1 if your node is named node1)*

   Like for the *command.core* queues, this queue is private for the current
   agent and makes it possible to direct a command to exactly the agent identified
   by *nodename*.

.. note::

    To learn how to specify the plugin's target queue, please read `Plugins <plugins>`_
    for more information.

Last but not least, the *AMQPService* binds to the queues mentioned above
and dispatches command calls to the *CommandRegistry*.

--------
"""
import sys
import re
import traceback
import logging
from zope.interface import implements
from qpid.messaging import Message
from qpid.messaging.message import Disposition
from qpid.messaging.constants import RELEASED
from gosa.common.json import loads, dumps, ServiceRequestNotTranslatable, BadServiceRequest
from gosa.common.handler import IInterfaceHandler
from gosa.common.components import PluginRegistry, AMQPWorker, ZeroconfService
from gosa.common.utils import parseURL, repr2json
from gosa.common import Environment


class AMQPService(object):
    """
    Class to serve all available queues and commands to the AMQP broker. It
    makes use of a couple of configuration flags provided by the gosa
    configurations file ``[amqp]`` section:

    ============== =============
    Key            Description
    ============== =============
    url            AMQP URL to connect to the broker
    id             User name to connect with
    key            Password to connect with
    command-worker Number of worker processes
    ============== =============

    Example::

        [amqp]
        url = amqps://amqp.intranet.gonicus.de:5671
        id = node1
        key = secret

    """
    implements(IInterfaceHandler)
    _priority_ = 1

    def __init__(self):
        env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.log.debug("initializing AMQP service provider")
        self.env = env

        self.__cr = None
        self.__zeroconf = None
        self.__cmdWorker = None

    def serve(self):
        """ Start AMQP service for this GOsa service provider. """
        # Load AMQP and Command registry instances
        amqp = PluginRegistry.getInstance('AMQPHandler')
        self.__cr = PluginRegistry.getInstance('CommandRegistry')

        # Create a list of queues we need here
        queues = {}
        for dsc in self.__cr.commands.values():
            queues[dsc['target']] = True

        # Finally create the queues
        for queue in queues:
            # Add round robin processor for queue
            self.__cmdWorker = AMQPWorker(self.env, connection=amqp.getConnection(),
                r_address='%s.command.%s; { create:always, node:{ type:queue, x-bindings:[ { exchange:"amq.direct", queue:"%s.command.%s" } ] } }' % (self.env.domain, queue, self.env.domain, queue),
                workers=self.env.config.get('amqp.command-worker', default=1),
                callback=self.commandReceived)

            # Add private processor for queue
            self.__cmdWorker = AMQPWorker(self.env, connection=amqp.getConnection(),
                    r_address='%s.command.%s.%s; { create:always, delete:receiver, node:{ type:queue, x-bindings:[ { exchange:"amq.direct", queue:"%s.command.%s.%s" } ] } }' % (self.env.domain, queue, self.env.id, self.env.domain, queue, self.env.id),
                workers=self.env.config.get('amqp.command-worker', default=1),
                callback=self.commandReceived)

        # Announce service
        url = parseURL(self.env.config.get("amqp.url"))
        self.__zeroconf = ZeroconfService(name="GOsa AMQP command service",
                port=url['port'],
                stype="_%s._tcp" % url['scheme'],
                text="path=%s\001service=gosa" % url['path'])
        self.__zeroconf.publish()

    def stop(self):
        """ Stop AMQP service for this GOsa service provider. """
        self.__zeroconf.unpublish()

    def commandReceived(self, ssn, message):
        """
        Process incoming commands, coming in with session and message
        information.

        ================= ==========================
        Parameter         Description
        ================= ==========================
        ssn               AMQP session object
        message           Received AMQP message
        ================= ==========================

        Incoming messages are coming from an
        :class:`gosa.common.components.amqp_proxy.AMQPServiceProxy` which
        is providing a *reply to* queue as a return channel. The command
        result is written to that queue.
        """

        # Check for id
        if not message.user_id:
            raise ValueError("incoming message without user_id")

        err = None
        res = None
        id_ = ''

        try:
            req = loads(message.content)
        except ServiceRequestNotTranslatable, e:
            err = str(e)
            req = {'id': id_}

        if err == None:
            try:
                id_ = req['id']
                name = req['method']
                args = req['params']

            except KeyError:
                err = str(BadServiceRequest(message.content))

        if not isinstance(args, list) and not isinstance(args, dict):
            raise ValueError("bad params %r: must be a list or dict" % args)

        # Extract source queue
        p = re.compile(r';.*$')
        queue = p.sub('', message._receiver.source)

        self.log.debug("received call [%s/%s] for %s: %s(%s)" % (id_, queue, message.user_id, name, args))

        # Don't process messages if the command registry thinks it's not ready
        if not self.__cr.processing.is_set():
            self.log.warning("waiting for registry to get ready")
            if not self.__cr.processing.wait(5):
                self.log.error("releasing call [%s/%s] for %s: %s(%s) - timed out" % (id_, queue, message.user_id, name, args))
                ssn.acknowledge(message, Disposition(RELEASED, set_redelivered=True))
                return

        # Try to execute either with or without keyword arguments
        if err == None:
            try:
                if isinstance(args, dict):
                    res = self.__cr.dispatch(message.user_id, queue, name, **args)
                else:
                    res = self.__cr.dispatch(message.user_id, queue, name, *args)

            # Catch everything that might happen in the dispatch, pylint: disable=W0703
            except Exception as e:
                text = traceback.format_exc()
                self.log.exception(text)
                err = str(e)
                exc_value = sys.exc_info()[1]

                # If message starts with [, it's a translateable message in
                # repr format
                if err.startswith("[") or err.startswith("("):
                    if err.startswith("("):
                        err = "[" + err[1:-1] + "]"
                    err = loads(repr2json(err))
                    err = dict(
                        name='JSONRPCError',
                        code=100,
                        message=str(exc_value),
                        error=err)

        self.log.debug("returning call [%s]: %s / %s" % (id_, res, err))

        response = dumps({"result": res, "id": id_, "error": err})
        ssn.acknowledge()

        # Talk to client generated reply queue
        sender = ssn.sender(message.reply_to)

        # Get rid of it...
        sender.send(Message(response))
