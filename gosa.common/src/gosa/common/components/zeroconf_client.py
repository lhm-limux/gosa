# -*- coding: utf-8 -*-
import select
import platform
from Queue import Queue

if platform.system() != "Windows":
    from gosa.common.components.dbus_runner import DBusRunner
    import dbus
    import avahi
else:
    from threading import Thread
    #pylint: disable=F0401
    import pybonjour


class ZeroconfException(Exception):
    pass


class ZeroconfClient(object):
    """
    The ZeroconfClient class helps with browsing for announced services. It
    creates a separate thread and needs the registrated service to look for
    as a parameter.

    Usage example::

        >>> import time
        >>> import ZerconfClient
        >>>
        >>> # This is the function called on changes
        >>> def callback(sdRef, flags, interfaceIndex, errorCode, fullname,
        ...                         hosttarget, port, txtRecord):
        ...   print('Resolved service:')
        ...   print('  fullname   =', fullname)
        ...   print('  hosttarget =', hosttarget)
        ...   print('  TXT        =', txtRecord)
        ...   print('  port       =', port)
        >>>
        >>> # Get instance and tell client to start
        >>> z= ZeroconfClient(['_amqps._tcp'], callback=callback)
        >>> z.start()
        >>>
        >>> # Do some sleep until someone presses Ctrl+C
        >>> try:
        >>>     while True:
        >>>         time.sleep(1)
        >>> except KeyboardInterrupt:
        >>>     # Shutdown client
        >>>     z.stop()
        >>>     exit()

    =============== ============
    Parameter       Description
    =============== ============
    regtypes        The service list to watch out for - i.e. _amqps._tcp
    timeout         The timeout in seconds
    callback        Method to call when we've received something
    domain          optional DNS domain to discover
    =============== ============
    """
    __resolved = []
    __services = {}
    oneshot = False

    def __init__(self, regtypes, timeout=2.0, callback=None, domain='local'):
        self.__timeout = timeout
        self.__callback = callback
        self.__regtypes = regtypes
        self.__domain = domain
        self.__server = None
        self.__thread = None
        self.__runner = None
        self.active = False

        if platform.system() != "Windows":
            self.start = self.startAvahi
            self.stop = self.stopAvahi
        else:
            self.start = self.startPybonjour
            self.stop = self.stopPybonjour


    def __get_path(self, txt):
        l = avahi.txt_array_to_string_array(txt)

        for k in l:
            if k[:5] == "path=":
                if k[5:].startswith("/"):
                    return k[5:]
                else:
                    return "/" + k[5:]

        return "/"

    def __get_service(self, txt):
        l = avahi.txt_array_to_string_array(txt)

        for k in l:
            if k[:8] == "service=":
                return k[8:]

        return None

    @staticmethod
    def discover(regs, domain=None):
        q = Queue()

        def done_callback(services):
            q.put(services)

        mdns = ZeroconfClient(regs, callback=done_callback)
        mdns.start()

        if domain:
            sddns = ZeroconfClient(regs, callback=done_callback, domain=domain)
            sddns.start()

        while True:
            urls = q.get()
            q.task_done()
            if urls:
                break

        if domain:
            sddns.stop()
        mdns.stop()

        return urls

    def startAvahi(self):
        self.__runner = DBusRunner.get_instance()
        bus = self.__runner.get_system_bus()
        self.__server = dbus.Interface(
                            bus.get_object(avahi.DBUS_NAME, '/'),
                            'org.freedesktop.Avahi.Server')

        # Register for all types we're interested in
        for reg_type in self.__regtypes:
            self.__registerServiceTypeAvahi(reg_type)

        self.__runner.start()

    def stopAvahi(self):
        self.__runner.stop()

    def __registerServiceTypeAvahi(self, reg_type):
        bus = self.__runner.get_system_bus()
        sbrowser = dbus.Interface(
                        bus.get_object(
                            avahi.DBUS_NAME,
                            self.__server.ServiceBrowserNew(
                                avahi.IF_UNSPEC,
                                avahi.PROTO_UNSPEC,
                                reg_type,
                                self.__domain,
                                dbus.UInt32(0))),
                       avahi.DBUS_INTERFACE_SERVICE_BROWSER)

        sbrowser.connect_to_signal("ItemNew", self.__newServiceAvahi)
        sbrowser.connect_to_signal("ItemRemove", self.__removeServiceAvahi)
        sbrowser.connect_to_signal("AllForNow", self.__allForNowAvahi)
        #sbrowser.connect_to_signal("Failure", self.__errorCallbackAvahi)

    #pylint: disable=W0613
    def __newServiceAvahi(self, interface, protocol, name, stype, domain, flags):
        #pylint: disable=W0612
        interface, protocol, name, stype, domain, host, aprotocol, address, port, txt, flags = self.__server.ResolveService(interface, protocol, name, stype, domain, avahi.PROTO_UNSPEC, dbus.UInt32(0))

        # Conversation to URL
        if port == 80:
            port = ''
        else:
            port = ':%i' % port

        if self.__get_service(txt) == "gosa":
            path = self.__get_path(txt)
            url = "%s://%s%s%s" % (stype[1:].split(".")[0], host, port, path)
            self.__services[(interface, protocol, name, stype, domain)] = url.encode('ascii')

    def __removeServiceAvahi(self, interface, protocol, name, stype, domain):
        del self.__services[(interface, protocol, name, stype, domain)]

    def __allForNowAvahi(self):
        self.__callback(self.__services.values())

    def __errorCallbackAvahi(self, *args):
        raise ZeroconfException("DBUS communication error: %s" % str(args[0]))

    def startPybonjour(self):
        self.active = True
        browse_sdRefs = []

        # Start the bonjour event processing.
        #pylint: disable=W0612
        for reg_type in self.__regtypes:
            browse_sdRefs.append(pybonjour.DNSServiceBrowse(regtype=self.__regtypes,
                callBack=self.__browseCallback))

        def runner():
            try:
                browse_sdRef = None
                while self.active:
                    ready = select.select(browse_sdRefs, [], [],
                        self.__timeout)

                    for browse_sdRef in browse_sdRefs:
                        if browse_sdRef in ready[0]:
                            pybonjour.DNSServiceProcessResult(browse_sdRef)
            finally:
                if browse_sdRef:
                    browse_sdRef.close()

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stopPybonjour(self):
        self.active = False
        self.__thread.join()

    def __resolveCallback(self, sdRef, flags, interfaceIndex, errorCode,
                        fullname, host, port, txt):
        if errorCode == pybonjour.kDNSServiceErr_NoError:

            # Conversation to URL
            if port == 80:
                port = ''
            else:
                port = ':%i' % port

            if self.__get_service(txt) == "gosa":
                path = self.__get_path(txt)
                url = "%s://%s%s%s" % (fullname.split(".")[-4:-3][0][1:], host, port, path)
                self.__callback([url.encode('ascii')])

            self.__resolved.append(True)

    def __browseCallback(self, sdRef, flags, interfaceIndex, errorCode,
                    serviceName, regtype, replyDomain):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return

        # Service removed
        if not (flags & pybonjour.kDNSServiceFlagsAdd):
            return

        # Service added
        resolve_sdRef = pybonjour.DNSServiceResolve(0,
            interfaceIndex,
            serviceName,
            regtype,
            replyDomain,
            self.__resolveCallback)

        try:
            while not self.__resolved:
                ready = select.select([resolve_sdRef], [], [], self.__timeout)
                if resolve_sdRef not in ready[0]:
                    pass
                pybonjour.DNSServiceProcessResult(resolve_sdRef)
            else:
                self.__resolved.pop()
        finally:
            resolve_sdRef.close()
