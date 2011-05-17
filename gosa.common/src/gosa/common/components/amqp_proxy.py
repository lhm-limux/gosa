# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_proxy.py 1212 2010-10-21 12:35:03Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
from qpid.messaging import *
from types import DictType
from gosa.common.components.jsonrpc_proxy import JSONRPCException
from jsonrpc.json import dumps, loads
from gosa.common.components.amqp import AMQPProcessor
from gosa.common.utils import parseURL, buildXMLSchema
from lxml import etree, objectify
from jsonrpc_proxy import ObjectFactory


class AMQPServiceProxy(object):
    """
    The AMQPServiceProxy provides a simple way to use GOsa RPC
    services from various clients. Using the proxy object, you
    can directly call methods without the need to know where
    it actually gets executed.

    Example:

    proxy = AMQPServiceProxy('amqp://admin:secret@localhost/org.gosa)
    print(proxy.getMethods())

    This will list the available methods.
    """

    def __init__(self, serviceURL, serviceAddress=None, serviceName=None,
                 conn=None, workers=3):
        """
        Instantiate the proxy object using the initializing parameters.

        @type serviceURL: string
        @param serviceURL: URL used to connect to the AMQP service broker
           user/password@host:port

        @type serviceAddress: string
        @param serviceAddress: Address string describing the target queue
           to bind to, must be skipped if no special queue is needed

        @type workers: int
        @param workers: Number of workers to allocate for processing
        """
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
            AMQPServiceProxy.worker = {"core": {}}

            # Prefill __serviceAddress correctly if domain is given
            if AMQPServiceProxy.domain:
                self.__serviceAddress= '%s.command.core' % AMQPServiceProxy.domain

            if not self.__serviceAddress:
                raise Exception("no serviceAddress or domain specified")

            # Pre instanciate core sessions
            for i in range(0, workers):
                ssn = conn.session(str(uuid4()))
                AMQPServiceProxy.worker["core"][i] = {
                        'ssn': ssn,
                        'sender': ssn.sender(self.__serviceAddress),
                        'receiver': ssn.receiver('reply-%s; {create:always, delete:always}' % ssn.name),
                        'locked': False}

        # Store connection
        self.__conn = conn
        self.__ssn = None

        # Retrieve methods
        try:
            AMQPServiceProxy.methods
        except:
            AMQPServiceProxy.methods= None
            AMQPServiceProxy.methods = self.getMethods()

            # If we've no direct queue, we need to push to different queues
            if AMQPServiceProxy.domain:
                queues= set([
                        x['target'] for x in AMQPServiceProxy.methods.itervalues()
                        if x['target'] != 'core'
                    ])

                # Pre instanciate queue sessions
                for queue in queues:
                    for i in range(0, workers):
                        ssn = conn.session(str(uuid4()))
                        AMQPServiceProxy.worker[queue]= {}
                        AMQPServiceProxy.worker[queue][i] = {
                                'ssn': ssn,
                                'sender': ssn.sender("%s.command.%s" %
                                    (AMQPServiceProxy.domain, queue)),
                                'receiver': ssn.receiver('reply-%s; {create:always, delete:always}' % ssn.name),
                                'locked': False}


    def close(self):
        """ Close the AMQP connection """

        # Close all senders/receivers
        for value in AMQPServiceProxy.worker.values():
            for vvalue in value.values():
                vvalue['sender'].close()
                vvalue['receiver'].close()

        self.__conn.close()

    def login(self, user, password):
        """ Dummy login """
        return True

    def logout(self):
        """ Dummy logout """
        return True

    def __getattr__(self, name):
        if self.__serviceName != None:
            name = "%s.%s" % (self.__serviceName, name)

        return AMQPServiceProxy(self.__serviceURL, self.__serviceAddress, name, self.__conn)

    def __call__(self, *args):
        if AMQPServiceProxy.methods:
            if not self.__serviceName in AMQPServiceProxy.methods:
                raise NameError("name '%s' not defined" % self.__serviceName)

            if AMQPServiceProxy.domain:
                queue= AMQPServiceProxy.methods[self.__serviceName]['target']
            else:
                queue= "core"
                #TODO: domain
        else:
            queue= "core"

        # Find free session for requested queue
        for sess, dsc in AMQPServiceProxy.worker[queue].iteritems():
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
            AMQPServiceProxy.worker[queue][self.__worker]['locked'] = False
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

                jc.insert(0, AMQPServiceProxy(self.__serviceURL, self.__serviceAddress, None, self.__conn))
                jc.append(data)
                AMQPServiceProxy.worker[queue][self.__worker]['locked'] = False
                return ObjectFactory.get_instance(*jc)

            AMQPServiceProxy.worker[queue][self.__worker]['locked'] = False
            return resp['result']


class AMQPEventConsumer(object):

    def __init__(self, url, domain="org.gosa", xquery=".", callback=None):

        # Build connection
        url = parseURL(url)
        self.__conn = Connection(url['url'], transport=url['transport'], reconnect=True)
        self.__conn.open()

        # Load defined event schema files
        schema_doc = buildXMLSchema(['gosa.common'], 'data/events', 'gosa.common', 'data/stylesheets/events.xsl')

        # Initialize parser
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self.__parser = objectify.makeparser(schema=schema)

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
        xml = objectify.fromstring(data.content, self.__parser)
        self.__callback(xml)

    def join(self):
        self.__eventWorker.join()


class AMQPStandaloneWorker(object):
    """
    AMQP standalone worker container. This object creates a number of worker threads
    for the defined sender and receiver addresses. It registers receiver
    callbacks for incoming packets.
    """
    sender = None
    receiver = None
    callback = None
    threads = []

    def __init__(self, connection, s_address=None, r_address=None, workers=0, callback=None):
        """
        Construct new AMQP worker threads depending on the supplied
        parameters.

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
            for i in range(workers):
                rcv = ssn.receiver(r_address, capacity=100)
                proc = AMQPProcessor(ssn, self.callback)
                proc.start()
                self.threads.append(proc)

    def join(self):
        for p in self.threads:
            p.join(1)
