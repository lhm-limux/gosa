# -*- coding: utf-8 -*-
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
    Module to publish our services with zeroconf using avahi.

    =============== ============
    Parameter       Description
    =============== ============
    name            service description
    port            port which is used by the service
    stype           service type (i.e. _http._tcp)
    domain          service type
    host            hostname to identify where the service runs
    text            additional descriptive text
    =============== ============
    """

    def __init__(self, name, port, stype="",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text[::-1]
        self.group = None

    def publish(self):
        """
        Start publishing the service.
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
        Stop publishing the service.
        """
        self.group.Reset()
