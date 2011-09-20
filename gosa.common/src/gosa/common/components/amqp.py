# -*- coding: utf-8 -*-
import platform
from threading import Thread
from qpid.messaging import *
from qpid.messaging.util import auto_fetch_reconnect_urls
from qpid.util import connect, ssl
from qpid.connection import Connection as DirectConnection
from lxml import etree, objectify

from gosa.common.utils import parseURL, makeAuthURL, buildXMLSchema
from gosa.common import Environment

# Import pythoncom for win32com / threads
if platform.system() == "Windows":
    #pylint: disable=F0401
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
        env = Environment.getInstance()
        env.log.debug("initializing AMQP handler")
        self.env = env
        self.config = env.config
        self.log = env.log

        # Enable debugging for qpid if we're in debug mode
        #if self.config.get('core.loglevel') == 'DEBUG':
        #    enable('qpid', DEBUG)

        # Evaluate username
        user = self.config.get("amqp.id", default=None)
        if not user:
            user = self.env.uuid
        password = self.config.get("amqp.key")

        # Load configuration
        self.url = parseURL(makeAuthURL(self.config.get('amqp.url'), user, password))
        self.reconnect = self.config.get('amqp.reconnect', True)
        self.reconnect_interval = self.config.get('amqp.reconnect_interval', 3)
        self.reconnect_limit = self.config.get('amqp.reconnect_limit', 0)

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
        self.log.debug("shutting down AMQP handler")
        self._conn.close()

    def start(self):
        """
        Enable AMQP queueing. This method puts up the event processor and
        sets it to "active".
        """
        self.log.debug("enabling AMQP queueing")

        # Evaluate username
        user = self.config.get("amqp.id", default=None)
        if not user:
            user = self.env.uuid
        password = self.config.get("amqp.key")

        # Create initial broker connection
        url = "%s:%s" % (self.url['host'], self.url['port'])
        self._conn = Connection.establish(url, reconnect=self.reconnect,
            username=user,
            password=password,
            transport=self.url['transport'],
            reconnect_interval=self.reconnect_interval,
            reconnect_limit=self.reconnect_limit)

        # Do automatic broker failover if requested
        if self.config.get('amqp.failover', False):
            auto_fetch_reconnect_urls(self._conn)

        # Create event exchange
        socket = connect(self.url['host'], self.url['port'])
        if self.url['scheme'][-1] == 's':
            socket = ssl(socket)
        user = self.config.get("amqp.id", default=None)
        if not user:
            user = self.env.uuid
        connection = DirectConnection(sock=socket,
                username=user,
                password=self.config.get("amqp.key"))
        connection.start()
        session = connection.session(str(uuid4()))
        # pylint: disable=E1103
        session.exchange_declare(exchange=self.env.domain, type="xml")
        connection.close()

        # Create event provider
        self._eventProvider = EventProvider(self.env, self.getConnection())

    def getConnection(self):
        """
        Returns an AMQP connection handle for further usage.

        ``Return:`` :class:`qpid.messaging.Connection`
        """
        return self._conn

    def checkAuth(self, user, password):
        """
        This function checks a username / password combination using
        the AMQP service' SASL configuration.

        =============== ============
        Parameter       Description
        =============== ============
        user            Username
        password        Password
        =============== ============

        ``Return:`` Bool, success or failure
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
            self.log.debug("AMQP service authentication reports: %s" % str(e))
            return False

        return True

    def sendEvent(self, data):
        """
        Send and validate an event thru AMQP service.

        =============== ============
        Parameter       Description
        =============== ============
        data            XML string or etree object representing the event.
        =============== ============

        ``Return:`` Bool, success or failure
        """
        try:
            event = "<?xml version='1.0' encoding='utf-8'?>\n"
            if isinstance(data, basestring):
                event += data
            else:
                event += etree.tostring(data, pretty_print=True)
            return self._eventProvider.send(event)

        except etree.XMLSyntaxError as e:
            if not isinstance(data, basestring):
                data = data.content
            if self.env:
                self.log.debug("event rejected (%s): %s" % (str(e), data))
            raise


class AMQPWorker(object):
    """
    AMQP worker container. This object creates a number of worker threads
    for the defined sender and receiver addresses. It registers receiver
    callbacks for incoming packets.

    =============== ============
    Parameter       Description
    =============== ============
    env             :class:`gosa.common.env.Environment` object
    connection      :class:`qpid.messaging.Connection` object
    s_address       address used to create a sender instance
    r_address       address used to create a receiver instance
    workers         number of worker threads
    callback        method to be called on incoming messages
    =============== ============

    """
    sender = None
    receiver = None
    callback = None

    def __init__(self, env, connection, s_address=None, r_address=None, workers=0, callback=None):
        self.env = env
        self.log = env.log

        self.callback = callback

        # Get reader handle
        ssn = connection.session()
        if s_address:
            self.log.debug("creating AMQP sender for %s" % s_address)
            self.sender = ssn.sender(s_address, capacity=100)

        # Get one receiver object or...
        if not r_address or workers == 0:
            self.receiver = None

        # ... start receive workers
        else:
            for i in range(workers):
                self.log.debug("creating AMQP receiver (%d) for %s" % (i, r_address))
                rcv = ssn.receiver(r_address, capacity=100)
                proc = AMQPProcessor(ssn, self.callback)
                proc.start()
                self.env.threads.append(proc)


class AMQPProcessor(Thread):
    """
    AMQP worker thread. This objects get instantiated by the AMQPWorker
    class. It is responsible for receiving the messages and calling the
    callback function.

    =============== ============
    Parameter       Description
    =============== ============
    ssn             AMQP session
    callback        method to be called when receiving AMQP messages
    =============== ============
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
        self.log = env.log

        # Prepare session and sender
        self.__sess = conn.session()
        self.__user = conn.username
        self.__sender = self.__sess.sender("%s/event" % env.domain)

    def send(self, data):
        #TODO: reject if not permitted
        self.log.debug("sending event: %s" % data)
        msg = Message(data)
        msg.user_id = self.__user
        return self.__sender.send(msg)


class EventConsumer(object):

    def __init__(self, env, conn, xquery=".", callback=None):
        self.env = env
        self.log = env.log

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
            node: {
                durable: False,
                x-declare: {
                    exclusive: True,
                    auto-delete: True }
            },
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
            self.log.debug("event received: %s" % data.content)
            self.__callback(xml)
        except etree.XMLSyntaxError as e:
            if self.env:
                self.log.debug("event rejected (%s): %s" % (str(e), data.content))
