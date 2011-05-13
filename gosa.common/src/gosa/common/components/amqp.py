# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp.py 1360 2010-11-15 13:42:15Z cajus $$

 This modules hosts AMQP related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import os
import traceback
import platform
from threading import Thread
from qpid.messaging import *
from qpid.messaging.util import auto_fetch_reconnect_urls
from qpid.log import enable, DEBUG, WARN
from qpid.util import URL, connect, ssl
from qpid.concurrency import synchronized
from qpid.connection import Connection as DirectConnection
from jsonrpc import loads, dumps, JSONEncodeException
from lxml import etree, objectify

from gosa.common.utils import parseURL, makeAuthURL, buildXMLSchema
from gosa.common.env import Environment

# Import pythoncom for win32com / threads
if platform.system() == "Windows":
    import pythoncom


class AMQPHandler(object):
    """
    This class handles the AMQP connection, incoming and outgoing connections.
    """
    _conn = None
    __capabilities = {}
    __peers = {}
    _eventProvider = None

    def __init__(self):
        """
        Construct a new AMQPHandler instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        env.log.debug("initializing AMQP handler")
        self.env = env

        # Enable debugging for qpid if we're in debug mode
        #if self.env.config.getOption('loglevel') == 'DEBUG':
        #    enable('qpid', DEBUG)

        # Evaluate username
        user = self.env.config.getOption("id", "amqp", default=None)
        if not user:
            user = self.env.uuid
        password = self.env.config.getOption("key", "amqp")

        # Load configuration
        self.url = parseURL(makeAuthURL(self.env.config.getOption('url', 'amqp'), user, password))
        self.reconnect = self.env.config.getOption('reconnect', 'amqp', True)
        self.reconnect_interval = self.env.config.getOption('reconnect_interval', 'amqp', 3)
        self.reconnect_limit = self.env.config.getOption('reconnect_limit', 'amqp', 0)

        # Load defined event schema files
        schema_doc = buildXMLSchema(['gosa.common'], 'data/events',
                'gosa.common', 'data/stylesheets/events.xsl')

        # Initialize parser
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self._parser = objectify.makeparser(schema=schema)

        # Go for it
        self.start()

    def __del__(self):
        self.env.log.debug("shutting down AMQP handler")
        self._conn.close()

    def start(self):
        """
        Enable AMQP queueing. This method puts up the event processor and
        sets it to "active".
        """
        self.env.log.debug("enabling AMQP queueing")

        # Evaluate username
        user = self.env.config.getOption("id", "amqp", default=None)
        if not user:
            user = self.env.uuid
        password = self.env.config.getOption("key", "amqp")

        # Create initial broker connection
        url = "%s:%s" % (self.url['host'], self.url['port'])
        self._conn = Connection.establish(url, reconnect=self.reconnect,
            username=user,
            password=password,
            transport=self.url['transport'],
            reconnect_interval=self.reconnect_interval,
            reconnect_limit=self.reconnect_limit)

        # Do automatic broker failover if requested
        if self.env.config.getOption('failover', 'amqp', False):
            auto_fetch_reconnect_urls(self._conn)

        # Create event exchange
        socket = connect(self.url['host'], self.url['port'])
        if self.url['scheme'][-1] == 's':
            socket = ssl(socket)
        user = self.env.config.getOption("id", "amqp", default=None)
        if not user:
            user = self.env.uuid
        connection = DirectConnection(sock=socket,
                username=user,
                password=self.env.config.getOption("key", "amqp"))
        connection.start()
        session = connection.session(str(uuid4()))
        # pylint: disable-msg=E1103
        session.exchange_declare(exchange=self.env.domain, type="xml")
        connection.close()

        # Create event provider
        self._eventProvider = EventProvider(self.env, self.getConnection())

    def getConnection(self):
        """
        Returns an AMQP connection handle for further usage.

        @rtype: L{qpid.messaging.Connection}
        @return: an AMQP connection
        """
        return self._conn

    def checkAuth(self, user, password):
        """
        This function checks a username / password combination using
        the AMQP service' SASL configuration.

        @type user: str
        @param user: username

        @type password: str
        @param password: password

        @rtype: bool
        @return: success or failure
        """
        # Strip username/password parts of url
        url = "%s:%s" % (self.url['host'], self.url['port'])

        # Don't allow blank authentication
        if user == "" or password == "":
            return False

        try:
            conn = Connection.establish(url, transport=self.url['transport'], username=user, password=password)
            conn.close()
        except ConnectionError, e:
            self.env.log.debug("AMQP service authentication reports: %s" % str(e))
            return False

        return True

    def sendEvent(self, data):
        # Validate event and let it pass if it matches the schema
        try:
            event = "<?xml version='1.0' encoding='utf-8'?>\n"
            if isinstance(data, basestring):
                event += data
            else:
                event += etree.tostring(data, pretty_print=True)
            xml = objectify.fromstring(event, self._parser)
            return self._eventProvider.send(event)
        except etree.XMLSyntaxError as e:
            if not isinstance(data, basestring):
                data = data.content
            if self.env:
                self.env.log.debug("event rejected (%s): %s" % (str(e), data))
            raise


class AMQPWorker(object):
    """
    AMQP worker container. This object creates a number of worker threads
    for the defined sender and receiver addresses. It registers receiver
    callbacks for incoming packets.
    """
    sender = None
    receiver = None
    callback = None

    def __init__(self, env, connection, s_address=None, r_address=None, workers=0, callback=None):
        """
        Construct new AMQP worker threads depending on the supplied
        parameters.

        @type env: Environment
        @param env: L{Environment} object

        @type connection: L{qpid.messaging.Connection}
        @param connection: AMQP connection

        @type s_address: string
        @param s_address: address used to create a sender instance

        @type r_address: string
        @param r_address: address used to create a receiver instance

        @type workers: int
        @param workers: number of worker threads

        @type callback: function
        @param callback: function to be called on incoming messages
        """
        self.env = env
        self.callback = callback

        # Get reader handle
        ssn = connection.session()
        if s_address:
            self.env.log.debug("creating AMQP sender for %s" % s_address)
            self.sender = ssn.sender(s_address, capacity=100)

        # Get one receiver object or...
        if not r_address or workers == 0:
            self.receiver = None

        # ... start receive workers
        else:
            for i in range(workers):
                self.env.log.debug("creating AMQP receiver (%d) for %s" % (i, r_address))
                rcv = ssn.receiver(r_address, capacity=100)
                proc = AMQPProcessor(ssn, self.callback)
                proc.start()
                self.env.threads.append(proc)


class AMQPProcessor(Thread):
    """
    AMQP worker thread. This objects get instanciated by the AMQPWorker
    class. It is responsible for receiving the messages and calling the
    callback function.
    """
    __callback = None
    __ssn = None

    def __init__(self, ssn, callback):
        Thread.__init__(self)
        self.setDaemon(True)
        self.__ssn = ssn
        self.__callback = callback

    def run(self):
        # Co-initialize COM for windows
        if platform.system() == "Windows":
            pythoncom.CoInitialize()

        while True:
            msg = self.__ssn.next_receiver().fetch()
            self.invokeCallback(msg)

    def invokeCallback(self, msg):
        return self.__callback(self.__ssn, msg)


class EventProvider(object):

    def __init__(self, env, conn):
        self.env = env

        # Prepare session and sender
        self.__sess = conn.session()
        self.__user = conn.username
        self.__sender = self.__sess.sender("%s/event" % env.domain)

    def send(self, data):
        #TODO: reject if not permitted
        self.env.log.debug("sending event: %s" % data)
        msg = Message(data)
        msg.user_id = self.__user
        return self.__sender.send(msg)


class EventConsumer(object):

    def __init__(self, env, conn, xquery=".", callback=None):
        """
        """
        self.env = env

        # Load defined event schema files
        schema_doc = buildXMLSchema(['gosa.common'], 'data/events',
                'gosa.common', 'data/stylesheets/events.xsl')

        # Initialize parser
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self._parser = objectify.makeparser(schema=schema)

        # Assemble subscription query
        queue = 'event-listener-%s' % uuid4()
        address = """%s; {
            create: always,
            delete:always,
            link: {
                x-bindings: [
                        {
                            exchange: '%s',
                            queue: %s,
                            key: event,
                            arguments: { xquery: %r}
                        }
                    ]
                }
            }""" % (queue, self.env.domain, queue, xquery)

        # Get session and create worker
        self.__sess = conn.session()

        # Add processor for core.event queue
        self.__callback = callback
        self.__eventWorker = AMQPWorker(self.env, connection=conn,
                        r_address=address,
                        workers=1,
                        callback=self.__eventProcessor)

    def __eventProcessor(self, ssn, data):
        #TODO: reject if sender is not permitted
        #print(data.user_id)

        # Validate event and let it pass if it matches the schema
        try:
            xml = objectify.fromstring(data.content, self._parser)
            self.env.log.debug("event received: %s" % data.content)
            self.__callback(xml)
        except etree.XMLSyntaxError as e:
            if self.env:
                self.env.log.debug("event rejected (%s): %s" % (str(e), data.content))
