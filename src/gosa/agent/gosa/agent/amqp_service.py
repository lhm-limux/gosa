# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_service.py 1267 2010-10-22 12:37:59Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import re
import traceback
from zope.interface import implements
from jsonrpc import loads, dumps, JSONEncodeException
from jsonrpc.serviceHandler import ServiceRequestNotTranslatable, BadServiceRequest
from qpid.messaging import *
from qpid.util import URL

from gosa.common.handler import IInterfaceHandler
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.amqp import AMQPWorker
from gosa.common.components.zeroconf import ZeroconfService
from gosa.common.utils import parseURL, repr2json
from gosa.common.env import Environment


class AMQPService(object):
    """
    Internal class to serve all available queues and commands to
    the AMQP broker.
    """
    implements(IInterfaceHandler)

    def __init__(self):
        """
        Construct a new AMQPService instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        env.log.debug("initializing AMQP service provider")
        self.env = env

    def serve(self):
        """ Start AMQP service for this GOsa service provider. """
        # Load AMQP and Command registry instances
        amqp = PluginRegistry.getInstance('AMQPHandler')
        self.__cr = PluginRegistry.getInstance('CommandRegistry')

        # Create a list of queues we need here
        queues = {}
        for command, dsc in self.__cr.commands.iteritems():
            queues[dsc['target']] = True

        # Finally create the queues
        for queue in queues:
            # Add round robin processor for queue
            self.__cmdWorker = AMQPWorker(self.env, connection=amqp.getConnection(),
                r_address='%s.command.%s; { create:always, node:{ type:queue, x-bindings:[ { exchange:"amq.direct", queue:"%s.command.%s" } ] } }' % (self.env.domain, queue, self.env.domain, queue),
                workers=self.env.config.getOption('command-worker', 'amqp', default=1),
                callback=self.commandReceived)

            # Add private processor for queue
            self.__cmdWorker = AMQPWorker(self.env, connection=amqp.getConnection(),
                    r_address='%s.command.%s.%s; { create:always, delete:receiver, node:{ type:queue, x-bindings:[ { exchange:"amq.direct", queue:"%s.command.%s.%s" } ] } }' % (self.env.domain, queue, self.env.id, self.env.domain, queue, self.env.id),
                workers=self.env.config.getOption('command-worker', 'amqp', default=1),
                callback=self.commandReceived)

        # Announce service
        url = parseURL(self.env.config.getOption("url", "amqp"))
        self.__zeroconf = ZeroconfService(name="GOsa AMQP command service",
                port=url['port'],
                stype="_gosa._tcp",
                text="%s://%s:%s/%s" % (url['scheme'], url['host'], url['port'], self.env.domain))
        self.__zeroconf.publish()

    def stop(self):
        """ Stop AMQP service for this GOsa service provider. """
        self.__zeroconf.unpublish()

    def commandReceived(self, ssn, message):
        """ Process incomming commands """

        # Check for id
        if not message.user_id:
            raise Exception("incoming message without user_id")

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
            except:
                err = str(BadServiceRequest(message.content))

        # Extract source queue
        p = re.compile(r';.*$')
        queue = p.sub('', message._receiver.source)

        self.env.log.debug("received call [%s/%s] for %s: %s(%s)" % (id_, queue, message.user_id, name, args))

        # Try to execute
        if err == None:
            try:
                res = self.__cr.dispatch(message.user_id, queue, name, *args)
            except Exception, e:
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

        self.env.log.debug("returning call [%s]: %s / %s" % (id_, res, err))

        response = dumps({"result": res, "id": id_, "error": err})
        ssn.acknowledge()

        # Talk to client generated reply queue
        sender = ssn.sender(message.reply_to)

        # Get rid of it...
        sender.send(Message(response))
