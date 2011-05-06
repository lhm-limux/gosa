# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: zeroconf.py 608 2010-08-16 08:12:35Z cajus $$

 This is the zeroconf provider module.

 See LICENSE for more information about the licensing.
"""
import sys
try:
    import avahi
except ImportError:
    print "Please install the python avahi module."
    sys.exit(1)

try:
    import dbus
except ImportError:
    print "Please install the python avahi module."
    sys.exit(1)


class ZeroconfService:
    """
    Module to publish our services with zeroconf using
    avahi.
    """

    def __init__(self, name, port, stype="",
                 domain="", host="", text=""):
        """
        Construct a new ZeroconfService object with the supplied parameters.

        @type name: str
        @param name: service description

        @type port: int
        @param port: port which is used by the service

        @type stype: str
        @param stype: service type (i.e. _http._tcp)

        @type domain: str
        @param domain: service type

        @type host: str
        @param host: hostname to identify where the service runs

        @type text: str
        @param text: additional descriptive text
        """
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text[::-1]

    def publish(self):
        """
        Start publishing the service
        """
        bus = dbus.SystemBus()
        server = dbus.Interface(
                         bus.get_object(
                                 avahi.DBUS_NAME,
                                 avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)

        g = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        g.Commit()
        self.group = g

    def unpublish(self):
        """
        Stop publishing the service
        """
        self.group.Reset()
