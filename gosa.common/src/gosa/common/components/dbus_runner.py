#-*- coding: utf-8
import sys
try:
    import dbus
except ImportError:
    print "Please install the python dbus module."
    sys.exit(1)

import gobject
from threading import Thread
from dbus.mainloop.glib import DBusGMainLoop
from dbus import glib


class DBusRunner(object):

    __bus = None
    __active = False
    __instance = None

    def __init__(self):
        loop = DBusGMainLoop()
        DBusRunner.__bus = dbus.SystemBus(mainloop=loop)

    def start(self):
        # Don't start us twice...
        if self.__active:
            return

        self.__active = True

        def runner():
            gobject.threads_init()
            glib.init_threads()
            context = gobject.MainLoop().get_context()

            while self.__active:
                context.iteration(True)

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stop(self):
        # Don't stop us twice
        if not self.__active:
            return

        self.__active = False
        self.__thread.join()

    def get_system_bus(self):
        return DBusRunner.__bus

    def is_active(self):
        return self.__active

    @staticmethod
    def get_instance():
        if not DBusRunner.__instance:
            DBusRunner.__instance = DBusRunner()
        return DBusRunner.__instance
