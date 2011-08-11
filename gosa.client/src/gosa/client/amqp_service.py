# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_service.py 1050 2010-10-08 06:55:44Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import netifaces
import traceback
from netaddr import IPNetwork
from zope.interface import implements
from jsonrpc import loads, dumps
from jsonrpc.serviceHandler import ServiceRequestNotTranslatable, BadServiceRequest
from qpid.messaging import *
from gosa.common.handler import IInterfaceHandler
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.amqp import AMQPWorker, EventConsumer
from gosa.common.event import EventMaker
from gosa.common import Environment


class AMQPClientService(object):
    """
    Internal class to serve all available queues and commands to
    the AMQP broker.
    """
    implements(IInterfaceHandler)
    _priority_ = 1

    def __init__(self):
        """
        Construct a new AMQPClientService instance based on the configuration
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
        amqp = PluginRegistry.getInstance('AMQPClientHandler')
        self.__cr = PluginRegistry.getInstance('ClientCommandRegistry')

        # Add private processor for client queue
        # pylint: disable-msg=E1101
        self.__cmdWorker = AMQPWorker(self.env, connection=amqp.getConnection(),
                r_address="""%s.client.%s; {
                    create:always,
                    node:{
                        type:queue,
                        x-bindings:[ {
                                exchange:"amq.direct",
                                queue:"%s.client.%s" } ]
                        }
                    }""" % (self.env.domain, self.env.uuid, self.env.domain, self.env.uuid),
            workers=self.env.config.get('amqp.command-worker', default=1),
            callback=self.commandReceived)

        # Add event processor
        EventConsumer(self.env,
            amqp.getConnection(),
            xquery="""
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:ClientPoll
            """,
            callback=self.__handleClientPoll)


        # Gather interface information
        self.__announce(True)

    def commandReceived(self, ssn, message):
        """ Process incoming commands """
        err = None
        res = None
        id_ = ''

        # Check for id
        if not message.user_id:
            raise Exception("incoming message without user_id")

        # Check for reply_to
        if not message.reply_to:
            raise Exception("incoming message without reply_to")

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

        self.env.log.debug("received call [%s] for %s: %s(%s)" % (id_, message.user_id, name, args))

        # Try to execute
        if err == None:
            try:
                res = self.__cr.dispatch(name, *args)
            except Exception, e:
                err = str(e)

                # Write exception to log
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.env.log.error(traceback.format_exception(exc_type, exc_value, exc_traceback))

        self.env.log.debug("returning call [%s]: %s / %s" % (id_, res, err))

        response = dumps({"result": res, "id": id_, "error": err})
        ssn.acknowledge()

        # Talk to client generated reply queue
        sender = ssn.sender(message.reply_to)

        # Get rid of it...
        sender.send(Message(response))

    def __handleClientPoll(self, data):
        self.env.log.debug("received client poll")
        self.__announce()

    def __announce(self, initial=False):
        amqp = PluginRegistry.getInstance('AMQPClientHandler')
        e = EventMaker()

        # Assemble network information
        more = []
        netinfo = []
        for interface in netifaces.interfaces():
            i_info = netifaces.ifaddresses(interface)

            # Skip lo interfaces
            if i_info[netifaces.AF_LINK][0]['addr'] == '00:00:00:00:00:00':
                continue

            # Skip lo interfaces
            if not netifaces.AF_INET in i_info:
                continue

            # Assemble ipv6 information
            ip6 = ""
            if netifaces.AF_INET6 in i_info:
                ip = IPNetwork("%s/%s" % (i_info[netifaces.AF_INET6][0]['addr'].split("%",1)[0],
                                        i_info[netifaces.AF_INET6][0]['netmask']))
                ip6 = str(ip)

            netinfo.append(
                e.NetworkDevice(
                    e.Name(interface),
                    e.IPAddress(i_info[netifaces.AF_INET][0]['addr']),
                    e.IPv6Address(ip6),
                    e.MAC(i_info[netifaces.AF_LINK][0]['addr']),
                    e.Netmask(i_info[netifaces.AF_INET][0]['netmask']),
                    e.Broadcast(i_info[netifaces.AF_INET][0]['broadcast'])))

        more.append(e.NetworkInformation(*netinfo))

        # Assemble capabilities
        caps = []
        for command, dsc in self.__cr.commands.iteritems():
            caps.append(
                e.ClientMethod(
                e.Name(command),
                e.Path(dsc['path']),
                e.Signature(','.join(dsc['sig'])),
                e.Documentation(dsc['doc'])))
        more.append(e.ClientCapabilities(*caps))

        # Build event
        info = e.Event(
            e.ClientAnnounce(
                e.Id(self.env.uuid),
                e.Name(self.env.id),
                *more))

        amqp.sendEvent(info)

        if not initial:
                try:
                    sk = PluginRegistry.getInstance('SessionKeeper')
                    sk.sendSessionNotification()
                except:
                    pass
