#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_service.py 1006 2010-09-30 12:43:58Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
import sys
import time
import re
import gettext
import netifaces
import ConfigParser
from urlparse import urlparse
from pkg_resources import resource_filename
from urllib import quote_plus as quote
from gosa.common.components.zeroconf_client import ZeroconfClient
from gosa.common.components.amqp_proxy import AMQPServiceProxy
from gosa.common.components.jsonrpc_proxy import JSONRPCException
from gosa.common.env import Environment
from gosa.common.utils import dmi_system
from qpid.messaging.exceptions import ConnectionError
from Crypto.Cipher import AES
from base64 import b64decode


# Include locales
t = gettext.translation('messages', resource_filename("gosa.client", "locale"), fallback=True)
_ = t.ugettext

class join_method(object):
    _url = None
    _need_config_refresh = False
    priority = None

    def __init__(self):
        self.env = Environment.getInstance()
        self.uuid = dmi_system("uuid")
        self.mac = self.get_mac_address()
        self.get_service()

    def url_builder(self, username, password):
        username = quote(username)
        password = quote(password)
        u = urlparse(self.url)
        return "%s://%s:%s@%s%s" % (u.scheme, username, password, u.netloc, u.path)

    def test_login(self):
        # No key set? Go away...
        if not self.key:
            self.env.log.warning("no machine key available - join required")
            return False

        # Prepare URL for login
        url = self.url_builder(self.svc_id, self.key)

        # Try to log in with provided credentials
        try:
            proxy = AMQPServiceProxy(url)
            self.env.log.debug("machine key is valid")
            return True
        except ConnectionError:
            self.env.log.warning("machine key is invalid - join required")
            return False

    def join(self, username, password, data=None):

        # Prepare URL for login
        url = self.url_builder(username, password)

        # Try to log in with provided credentials
        try:
            proxy = AMQPServiceProxy(url)
        except ConnectionError as e:
            self.env.log.error("connection to AMQP failed: %s" % str(e))
            self.show_error(_("Cannot join client: check user name or password!"))
            return None

        # Try to join client
        try:
            key, uuid = proxy.joinClient(u"" + self.uuid, self.mac, data)
        except JSONRPCException as e:
            self.show_error(e.error.capitalize())
            self.env.log.error(e.error)
            return None

        # If key is present, write info back to file
        if key:
            self.env.log.debug("client '%s' joined with key '%s'" % (self.uuid, key))
            config = self.env.config.getOption("config")
            parser = ConfigParser.RawConfigParser()
            parser.read(config)

            # Section present?
            try:
                url = parser.get("amqp", "url")
            except ConfigParser.NoSectionError:
                parser.add_section("amqp")

            # Set url and key
            parser.set("amqp", "url", self.url)
            parser.set("core", "id", uuid)
            parser.set("amqp", "key", key)

            # Write back to file
            with open(config, "wb") as f:
                parser.write(f)

        return key

    def decrypt(self, key, data):
        key_pad = AES.block_size - len(key) % AES.block_size
        if key_pad != AES.block_size:
            key += chr(key_pad) * key_pad
        data = AES.new(key, AES.MODE_ECB).decrypt(data)
        return data[:-ord(data[-1])]

    def get_service_from_config(self):
        url = self.env.config.getOption("url", "amqp", default=None)
        sys_id = self.env.config.getOption("id", default=None)
        key = self.env.config.getOption("key", "amqp", default=None)
        return (url, sys_id, key)

    def get_service(self):

        # Try to load url/key from configuration
        (svc_url, svc_id, svc_key) = self.get_service_from_config()
        if svc_url and svc_key:
            self.svc_id = svc_id if svc_id else self.uuid
            self.url = svc_url
            self.key = svc_key
            return

        #TODO: Not M$ compatible - not sure if we'll ever join
        #      these kind of clients
        with open("/proc/cmdline", "r") as f:
            line = f.readlines()[0]

        # Scan command line for svc_ entries
        for dummy, var, data in re.findall(r"(([a-z0-9_]+)=([^\s]+))",
            line, flags=re.IGNORECASE):

            # Save relevant values
            if var == "svc_url":
                svc_url = data
            if var == "svc_key":
                tmp = self.decrypt(self.uuid.replace("-", ""), b64decode(data))
                svc_id = tmp[0:36]
                svc_key = tmp[36:]
                self._need_config_refresh = True

        # If there's no url, try to find it using zeroconf
        if not svc_url:
            self.env.log.info("Searching service provider...")
            zclient = ZeroconfClient('_gosa._tcp', callback=self.update_url)
            zclient.start()
            try:
                while not self._url:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                # Shutdown client
                zclient.stop()
                sys.exit(1)
            zclient.stop()
            svc_url = self._url

        self.svc_id = svc_id
        self.url = svc_url
        self.key = svc_key

        if self._need_config_refresh:
            config = self.env.config.getOption("config")
            parser = ConfigParser.RawConfigParser()
            parser.read(config)

            # Section present?
            try:
                parser.get("amqp", "url")
            except ConfigParser.NoSectionError:
                parser.add_section("amqp")

            # Set url and key
            parser.set("amqp", "url", self.url)
            parser.set("core", "id", self.svc_id)
            parser.set("amqp", "key", self.key)

            # Write back to file
            with open(config, "wb") as f:
                parser.write(f)

    def get_mac_address(self):
        for interface in netifaces.interfaces():
            i_info = netifaces.ifaddresses(interface)

            # Skip lo interfaces
            if i_info[netifaces.AF_LINK][0]['addr'] == '00:00:00:00:00:00':
                continue

            # Skip lo interfaces
            if not netifaces.AF_INET in i_info:
                continue

            return i_info[netifaces.AF_LINK][0]['addr']

        return None

    def update_url(self, sdRef, flags, interfaceIndex, errorCode, fullname,
                hosttarget, port, txtRecord):
        # Don't do this twice for amqp. We've automatic fallback.
        if self._url:
            return

        rx = re.compile(r'^amqps?://')
        if rx.match(txtRecord):
            self.env.log.info("using service '%s'" % txtRecord)
            self._url = txtRecord

    def start_gui(self):
        pass

    def end_gui(self):
        pass

    def show_error(self, error):
        pass

    @staticmethod
    def available():
        return False
