import select
import sys
import platform
from threading import Thread

if platform.system() != "Windows":
    import dbus
    import gobject
    import avahi
    from dbus import DBusException
    from dbus.mainloop.glib import DBusGMainLoop
    from dbus import glib
else:
    import pybonjour


class ZeroconfClient(object):
    """
    The ZeroconfClient class helps with browsing for announced services. It
    creates a separate thread and needs the registrated service to look for
    as a parameter.

    Usage example:
        import time
        import ZerconfClient

        # This is the function called on changes
        def callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                                 hosttarget, port, txtRecord):
           print('Resolved service:')
           print('  fullname   =', fullname)
           print('  hosttarget =', hosttarget)
           print('  TXT        =', txtRecord)
           print('  port       =', port)

        # Get instance and tell client to start
        z= ZeroconfClient('_gosa._tcp', callback=callback)
        z.start()

        # Do some sleep until someone presses Ctrl+C
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Shutdown client
            z.stop()
            exit()
    """
    __resolved = []

    def __init__(self, regtype, timeout=2.0, callback=None):
        """
        Create a new instance of the ZeroconfClient using the
        provided parameters.

        @type regtype: string
        @param regtype: The service to watch out for - i.e. _gosa._tcp
        """
        self.__timeout = timeout
        self.__callback = callback
        self.__regtype = regtype

    def start(self):

        if platform.system() == "Linux":

            loop = DBusGMainLoop()
            self.__bus = dbus.SystemBus(mainloop=loop)
            self.__server = dbus.Interface(
                                self.__bus.get_object(avahi.DBUS_NAME, '/'),
                                'org.freedesktop.Avahi.Server')
            sbrowser = dbus.Interface(self.__bus.get_object(avahi.DBUS_NAME,
                           self.__server.ServiceBrowserNew(avahi.IF_UNSPEC,
                           avahi.PROTO_UNSPEC, self.__regtype, 'local',
                           dbus.UInt32(0))),
                           avahi.DBUS_INTERFACE_SERVICE_BROWSER)
            sbrowser.connect_to_signal("ItemNew", self.__browseCallbackAvahi)
            self.active = True

        else:
            """
            Start the bonjour event processing.
            """
            self.active = True
            browse_sdRef = pybonjour.DNSServiceBrowse(regtype=self.__regtype,
            callBack=self.__browseCallback)

        def runner():
            if platform.system() == "Linux":
                gobject.threads_init()
                glib.init_threads()
                context = gobject.MainLoop().get_context()

                while self.active:
                    context.iteration(True)

            else:
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
        Stop the bonjour event processing.
        """
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

        # get txt record from dbus.Array
        txtRecord = ""
        for i in args[9]:
            txtRecord += chr(i[0])

        self.__callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                        hosttarget, port, txtRecord)
        self.__resolved.append(True)

    def __errorCallbackAvahi(self, *args):
        #TODO: Remove me or throw exceptions
        print('error_handler: ')
        print(args[1])
