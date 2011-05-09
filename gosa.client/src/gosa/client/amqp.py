# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp.py 1057 2010-10-08 10:03:03Z cajus $$

 This modules hosts AMQP related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import os
import re
import time
import traceback
from urlparse import urlparse
from qpid.messaging import *
from qpid.messaging.util import auto_fetch_reconnect_urls
from qpid.log import enable, DEBUG, WARN
from qpid.util import URL, connect
from qpid.concurrency import synchronized
from jsonrpc import loads, dumps, JSONEncodeException
from lxml import etree, objectify

from gosa.common.components.amqp import AMQPHandler, AMQPWorker, EventProvider
from gosa.common.components.command import Command
from gosa.common.components.zeroconf_client import ZeroconfClient
from gosa.common.utils import parseURL, buildXMLSchema
from gosa.common.env import Environment


class AMQPClientHandler(AMQPHandler):
    """
    This class handles the AMQP connection, incoming and outgoing connections
    and allows event callback registration.
    """
    _conn = None
    __capabilities = {}
    __peers = {}
    _eventProvider = None
    __zclient = None
    url = None
    joined = False

    def __init__(self):
        """
        Construct a new AMQPClientHandler instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        env.log.debug("initializing AMQP client handler")
        self.env = env

        # Enable debugging for qpid if we're in debug mode
        #if self.env.config.getOption('loglevel') == 'DEBUG':
        #    enable('qpid', DEBUG)

        # Load configuration
        self.url = parseURL(self.env.config.getOption('url', 'amqp', None))
        self.domain = self.env.config.getOption('domain', 'amqp', default="org.gosa")

        # Use zeroconf if there's no URL
        if not self.url:
            self.__zclient = ZeroconfClient('_gosa._tcp', callback=self.updateURL)
            self.__zclient.start()

            # Wait for valid URL to continue
            self.env.log.info("Searching service provider...")
            while not self.url:
                time.sleep(0.5)

            # Stop zeroconf resolution
            self.__zclient.stop()

        # Set params and go for it
        self.reconnect = self.env.config.getOption('reconnect', 'amqp', True)
        self.reconnect_interval = self.env.config.getOption('reconnect-interval', 'amqp', 3)
        self.reconnect_limit = self.env.config.getOption('reconnect-limit', 'amqp', 0)

        # Check if credentials are supplied
        if not self.env.config.getOption("key", "amqp"):
            raise Exception("no key supplied - please join the client")

        # Load defined event schema files
        schema_doc = buildXMLSchema('gosa.common', 'data/events', 'data/stylesheets/events.xsl')

        # Initialize parser
        schema_root = etree.XML(schema_doc)
        schema = etree.XMLSchema(schema_root)
        self._parser = objectify.makeparser(schema=schema)

        # Start connection
        self.start()

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

        # Create initial broker connection
        url = "%s:%s" % (self.url['host'], self.url['port'])
        self._conn = Connection.establish(url, reconnect=self.reconnect,
            username=user,
            password=self.env.config.getOption("key", "amqp"),
            transport=self.url['transport'],
            reconnect_interval=self.reconnect_interval,
            reconnect_limit=self.reconnect_limit)

        # Do automatic broker failover if requested
        if self.env.config.getOption('failover', 'amqp', False):
            auto_fetch_reconnect_urls(self._conn)

        # Create event provider
        self._eventProvider = EventProvider(self.env, self._conn)


    def updateURL(self, sdRef, flags, interfaceIndex, errorCode, fullname,
                hosttarget, port, txtRecord):
        # Don't do this twice for amqp. We've automatic fallback.
        if self.url:
            return

        rx = re.compile(r'^amqps?://')
        if rx.match(txtRecord):
            o = urlparse(txtRecord)
            # pylint: disable-msg=E1101
            self.domain = o.path[1::]
            self.env.log.info("using service '%s'" % txtRecord)

            # Configure system
            user = self.env.config.getOption('id', 'amqp', default=None)
            if not user:
                user = self.env.uuid
            key = self.env.config.getOption('key', 'amqp')
            if key:
                # pylint: disable-msg=E1101
                self.url = parseURL('%s://%s:%s@%s' % (o.scheme, user, key, o.netloc))
            else:
                self.url = parseURL(txtRecord)

    def __del__(self):
        self.env.log.debug("shutting down AMQP client handler")
        self._conn.close()
