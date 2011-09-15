#-*- coding: utf-8
import sys
try:
    import dbus

except ImportError:
    print "Please install the python dbus module."
    sys.exit(1)

import gobject
import time
from threading import Thread
from dbus.mainloop.glib import DBusGMainLoop
from dbus import glib


class DBusRunner(object):
    """
    The *DBusRunner* module acts as a singleton for the DBUS system
    bus. Interested instances can obtain the system bus from the
    runner.
    """
    __bus = None
    __active = False
    __instance = None

    def __init__(self):
        loop = DBusGMainLoop()
        DBusRunner.__bus = dbus.SystemBus(mainloop=loop)

    def start(self):
        """
        Start the :func:`gobject.MainLoop` to establish DBUS communications.
        """
        if self.__active:
            return

        self.__active = True

        def runner():
            gobject.threads_init()
            glib.init_threads()
            context = gobject.MainLoop().get_context()
            while self.__active:
                context.iteration(False)
                if not context.pending():
                    time.sleep(1)

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stop(self):
        """
        Stop the :func:`gobject.MainLoop` to shut down DBUS communications.
        """
        # Don't stop us twice
        if not self.__active:
            return

        self.__active = False
        self.__thread.join()

    def get_system_bus(self):
        """
        Return the current DBUS system bus.

        ``Return:`` DBusRunner bus object
        """
        return DBusRunner.__bus

    def is_active(self):
        """
        Return the current DBUS system bus.

        ``Return:`` Bool value
        """
        return self.__active

    @staticmethod
    def get_instance():
        """
        Singleton to return a DBusRunner object.

        ``Return:`` :class:`gosa.common.dbus_runner.DBusRunner`
        """
        if not DBusRunner.__instance:
            DBusRunner.__instance = DBusRunner()
        return DBusRunner.__instance
