# -*- coding: utf-8 -*-
import select
import platform

if platform.system() != "Windows":
    from gosa.common.components.dbus_runner import DBusRunner
    import dbus
    import avahi
else:
    from threading import Thread
    import pybonjour


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
        >>> z= ZeroconfClient('_gosa._tcp', callback=callback)
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
    regtype         The service to watch out for - i.e. _gosa._tcp
    timeout         The timeout in seconds
    callback        Method to call when we've received something
    =============== ============
    """
    __resolved = []

    def __init__(self, regtype, timeout=2.0, callback=None, domain='local'):
        self.__timeout = timeout
        self.__callback = callback
        self.__regtype = regtype
        self.domain = domain

    def start(self):
        """
        Start zeroconf event processing.
        """

        if platform.system() == "Linux":
            self.__runner = DBusRunner.get_instance()
            bus = self.__runner.get_system_bus()
            self.__server = dbus.Interface(
                                bus.get_object(avahi.DBUS_NAME, '/'),
                                'org.freedesktop.Avahi.Server')
            sbrowser = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
                           self.__server.ServiceBrowserNew(avahi.IF_UNSPEC,
                           avahi.PROTO_UNSPEC, self.__regtype, self.domain,
                           dbus.UInt32(0))),
                           avahi.DBUS_INTERFACE_SERVICE_BROWSER)
            sbrowser.connect_to_signal("ItemNew", self.__browseCallbackAvahi)
            self.__runner.start()

        else:
            self.active = True

            # Start the bonjour event processing.
            browse_sdRef = pybonjour.DNSServiceBrowse(regtype=self.__regtype,
            callBack=self.__browseCallback)

            def runner():
                try:
                    while self.active:
                        ready = select.select([browse_sdRef], [], [],
                            self.__timeout)
                        if browse_sdRef in ready[0]:
                            pybonjour.DNSServiceProcessResult(browse_sdRef)
                finally:
                    browse_sdRef.close()

            self.__thread = Thread(target=runner)
            self.__thread.start()

    def stop(self):
        """
        Stop the zeroconf event processing.
        """
        if platform.system() == "Linux":
            self.__runner.stop()

        else:
            self.active = False
            self.__thread.join()

    def __resolveCallback(self, sdRef, flags, interfaceIndex, errorCode,
                        fullname, hosttarget, port, txtRecord):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            txtRecord = ''.join(txtRecord.split('\x01'))
            self.__callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                                     hosttarget, port, txtRecord)
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

    def __browseCallbackAvahi(self, interface, protocol, name, stype, domain,
                              flags):
        if flags & avahi.LOOKUP_RESULT_LOCAL:
                # local service, skip
                pass

        self.__server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.__resolveCallbackAvahi,
            error_handler=self.__errorCallbackAvahi)

    def __resolveCallbackAvahi(self, *args):
        sdRef = ""
        flags = args[10]
        interfaceIndex = args[0]
        errorCode = 0
        fullname = args[2]
        hosttarget = args[7]
        port = args[8]

        txtRecord = ''.join(avahi.txt_array_to_string_array(args[9]))

        self.__callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                        hosttarget, port, txtRecord)
        self.__resolved.append(True)

    def __errorCallbackAvahi(self, *args):
        #TODO: Remove me or throw exceptions
        print('error_handler: ')
        print(args[1])
