# -*- coding: utf-8 -*-
from qpid.messaging import Connection, Message, uuid4
from types import DictType
from gosa.common.components.jsonrpc_proxy import JSONRPCException, ObjectFactory
from gosa.common.json import dumps, loads
from gosa.common.components.amqp import AMQPProcessor
from gosa.common.utils import parseURL
from lxml import objectify


class AMQPServiceProxy(object):
    """
    The AMQPServiceProxy provides a simple way to use GOsa RPC
    services from various clients. Using the proxy object, you
    can directly call methods without the need to know where
    it actually gets executed::

        >>> from gosa.common.components import AMQPServiceProxy
        >>> proxy = AMQPServiceProxy('amqp://admin:secret@localhost/org.gosa')
        >>> proxy.getMethods()

    This will return a dictionary describing the available methods.

    =============== ============
    Parameter       Description
    =============== ============
    serviceURL      URL used to connect to the AMQP service broker
    serviceAddress  Address string describing the target queue to bind to, must be skipped if no special queue is needed
    serviceName     *internal*
    conn            *internal*
    workers         Number of workers to allocate for processing
    =============== ============

    The AMQPService proxy creates a temporary AMQP *reply to* queue, which
    is used for command results.
    """
    worker = {}

    def __init__(self, serviceURL, serviceAddress=None, serviceName=None,
                 conn=None, workers=3):
        self.__URL = url = parseURL(serviceURL)
        self.__serviceURL = serviceURL
        self.__serviceName = serviceName
        self.__serviceAddress = serviceAddress
        self.__workers = workers
        domain = url['path']

        # Prepare AMQP connection if not already there
        if not conn:
            conn = Connection(url['url'], transport=url['transport'], reconnect=True)
            conn.open()
            AMQPServiceProxy.domain= domain

            # Prefill __serviceAddress correctly if domain is given
            if AMQPServiceProxy.domain:
                self.__serviceAddress = '%s.command.core' % AMQPServiceProxy.domain

            if not self.__serviceAddress:
                raise Exception("no serviceAddress or domain specified")

            try:
                AMQPServiceProxy.worker[self.__serviceAddress]
            except:
                AMQPServiceProxy.worker[self.__serviceAddress] = {}

            # Pre instanciate core sessions
            for i in range(0, workers):
                ssn = conn.session(str(uuid4()))
                AMQPServiceProxy.worker[self.__serviceAddress][i] = {
                        'ssn': ssn,
                        'sender': ssn.sender(self.__serviceAddress),
                        'receiver': ssn.receiver('reply-%s; {create:always, delete:always, node: { type: queue, durable: False, x-declare: { exclusive: False, auto-delete: True } }}' % ssn.name),
                        'locked': False}

        # Store connection
        self.__conn = conn
        self.__ssn = None

        # Retrieve methods
        try:
            AMQPServiceProxy.methods
        except:
            AMQPServiceProxy.methods = None
            AMQPServiceProxy.methods = {}

        # Retrieve methods
        try:
            AMQPServiceProxy.methods[self.__serviceAddress]
        except:
            AMQPServiceProxy.methods[self.__serviceAddress] = None
            AMQPServiceProxy.methods[self.__serviceAddress] = self.getMethods()

            # If we've no direct queue, we need to push to different queues
            if AMQPServiceProxy.domain:
                queues = set([
                        x['target'] for x in AMQPServiceProxy.methods[self.__serviceAddress].itervalues()
                        if x['target'] != 'core'
                    ])

                # Pre instanciate queue sessions
                for queue in queues:
                    for i in range(0, workers):
                        ssn = conn.session(str(uuid4()))
                        AMQPServiceProxy.worker[queue] = {}
                        AMQPServiceProxy.worker[queue][i] = {
                                'ssn': ssn,
                                'sender': ssn.sender("%s.command.%s" %
                                    (AMQPServiceProxy.domain, queue)),
                                'receiver': ssn.receiver('reply-%s; {create:always, delete:always, node: { type: queue, durable: False, x-declare: { exclusive: False, auto-delete: True } }}' % ssn.name),
                                'locked': False}


    def close(self):
        """
        Close the AMQP connection established by the proxy.
        """

        # Close all senders/receivers
        for value in AMQPServiceProxy.worker.values():
            for vvalue in value.values():
                vvalue['sender'].close()
                vvalue['receiver'].close()

        self.__conn.close()

    #pylint: disable=W0613
    def login(self, user, password):
        return True

    def logout(self):
        return True

    def __getattr__(self, name):
        if self.__serviceName != None:
            name = "%s.%s" % (self.__serviceName, name)

        return AMQPServiceProxy(self.__serviceURL, self.__serviceAddress, name,
                self.__conn, workers=self.__workers)

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0 and len(args) > 0:
            raise JSONRPCException("JSON-RPC does not support positional and keyword arguments at the same time")

        # Default to 'core' queue
        queue = "core"

        if AMQPServiceProxy.methods[self.__serviceAddress]:
            if not self.__serviceName in AMQPServiceProxy.methods[self.__serviceAddress]:
                raise NameError("name '%s' not defined" % self.__serviceName)

            if AMQPServiceProxy.domain:
                queue = AMQPServiceProxy.methods[self.__serviceAddress][self.__serviceName]['target']
            else:
                queue = self.__serviceAddress

        # Find free session for requested queue
        for sess, dsc in AMQPServiceProxy.worker[self.__serviceAddress].iteritems():
            if not dsc['locked']:
                self.__ssn = dsc['ssn']
                self.__sender = dsc['sender']
                self.__receiver = dsc['receiver']
                self.__worker = sess
                dsc['locked'] = True
                break

        # No free session?
        if not self.__ssn:
            raise Exception('no free session - increase workers')

        # Send
        if len(kwargs):
            postdata = dumps({"method": self.__serviceName, 'params': kwargs, 'id': 'jsonrpc'})
        else:
            postdata = dumps({"method": self.__serviceName, 'params': args, 'id': 'jsonrpc'})

        message = Message(postdata)
        message.user_id = self.__URL['user']
        message.reply_to = 'reply-%s' % self.__ssn.name
        self.__sender.send(message)

        # Get response
        respdata = self.__receiver.fetch()
        resp = loads(respdata.content)
        self.__ssn.acknowledge(respdata)

        if resp['error'] != None:
            AMQPServiceProxy.worker[self.__serviceAddress][self.__worker]['locked'] = False
            raise JSONRPCException(resp['error'])

        else:
            # Look for json class hint
            if "result" in resp and \
                isinstance(resp["result"], DictType) and \
                "__jsonclass__" in resp["result"] and \
                resp["result"]["__jsonclass__"][0] == "json.ObjectFactory":

                resp = resp["result"]
                jc = resp["__jsonclass__"][1]
                del resp["__jsonclass__"]

                # Extract property presets
                data = {}
                for prop in resp:
                    data[prop] = resp[prop]

                jc.insert(0, AMQPServiceProxy(self.__serviceURL,
                    self.__serviceAddress, None, self.__conn,
                    workers=self.__workers))
                jc.append(data)
                AMQPServiceProxy.worker[self.__serviceAddress][self.__worker]['locked'] = False
                return ObjectFactory.get_instance(*jc)

            AMQPServiceProxy.worker[self.__serviceAddress][self.__worker]['locked'] = False
            return resp['result']


class AMQPEventConsumer(object):
    """
    The AMQPEventConsumer can be used to subscribe for events
    and process them thru a callback. The subscription is done
    thru *XQuery*, the callback can be a python method.

    Example listening for an event called *AsteriskNotification*::

        >>> from gosa.common.components import AMQPEventConsumer
        >>> from lxml import etree
        >>>
        >>> # Event callback
        >>> def process(data):
        ...     print(etree.tostring(data, pretty_print=True))
        >>>
        >>> # Create event consumer
        >>> consumer = AMQPEventConsumer("amqps://admin:secret@localhost/org.gosa",
        ...             xquery=\"\"\"
        ...                 declare namespace f='http://www.gonicus.de/Events';
        ...                 let $e := ./f:Event
        ...                 return $e/f:AsteriskNotification
        ...             \"\"\",
        ...             callback=process)

    The consumer will start right away, listening for your events.

    =============== ============
    Parameter       Description
    =============== ============
    url             URL used to connect to the AMQP service broker
    domain          If the domain is not already encoded in the URL, it can be specified here.
    xquery          `XQuery <http://en.wikipedia.org/wiki/XQuery>`_ string to query for events.
    callback        Python method to be called if the event happened.
    =============== ============

    .. note::
       The AMQP URL consists of these parts::

         (amqp|amqps)://user:password@host:port/domain
    """

    def __init__(self, url, domain="org.gosa", xquery=".", callback=None):

        # Build connection
        url = parseURL(url)
        self.__conn = Connection(url['url'], transport=url['transport'], reconnect=True)
        self.__conn.open()

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
            }""" % (queue, domain, queue, xquery)

        # Add processor for core.event queue
        self.__callback = callback
        self.__eventWorker = AMQPStandaloneWorker(
                        self.__conn,
                        r_address=address,
                        workers=1,
                        callback=self.__eventProcessor)

    def __del__(self):
        self.__eventWorker.join()
        self.__conn.close()

    def __eventProcessor(self, ssn, data):
        # Call callback, let exceptions pass to the caller
        xml = objectify.fromstring(data.content)
        self.__callback(xml)

    def join(self):
        self.__eventWorker.join()


class AMQPStandaloneWorker(object):
    """
    AMQP standalone worker container. This object creates a number of worker threads
    for the defined sender and receiver addresses. It registers receiver
    callbacks for incoming packets.

    =============== ============
    Parameter       Description
    =============== ============
    connection      :class:`qpid.messaging.Connection`
    s_address       Address used to create a sender instance
    r_address       Address used to create a receiver instance
    workers         Number of worker threads
    callback        method to be called on incoming messages
    =============== ============
    """
    sender = None
    receiver = None
    callback = None
    threads = []

    def __init__(self, connection, s_address=None, r_address=None, workers=0, callback=None):
        self.callback = callback

        # Get reader handle
        ssn = connection.session()
        if s_address:
            self.sender = ssn.sender(s_address, capacity=100)

        # Get one receiver object or...
        if not r_address or workers == 0:
            self.receiver = None

        # ... start receive workers
        else:
            #pylint: disable=W0612
            for i in range(workers):
                ssn.receiver(r_address, capacity=100)
                proc = AMQPProcessor(ssn, self.callback)
                proc.start()
                self.threads.append(proc)

    def join(self):
        """
        Join the worker threads.
        """
        for p in self.threads:
            p.join(1)
