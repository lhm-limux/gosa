#!/usr/bin/env python
from threading import Thread
import sys
import time
import gobject
import dbus
import dbus.service
import dbus.glib
from dbus.mainloop.glib import DBusGMainLoop


class SignalManager(object):

    def start(self):

        def runner():
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.__bus = dbus.SystemBus()
            name = dbus.service.BusName('org.example.test', self.__bus)
            self.__object = TestObject(self.__bus)
            self.active = True
            loop = gobject.MainLoop()
            gobject.threads_init()
            dbus.glib.init_threads()
            context = gobject.MainLoop().get_context()

            while self.active:
                context.iteration(True)

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stop(self):
        self.active = False
        self.__thread.join()

    def send(self, text):
    	self.__object.HelloSignal(text)


class TestObject(dbus.service.Object):

    def __init__(self, conn, object_path='/org/example/test/TestObject/object'):
        dbus.service.Object.__init__(self, conn, object_path)

    @dbus.service.signal('org.example.test')
    def HelloSignal(self, message):
        print "[HelloSignal]", message 


if __name__ == '__main__':
    sm = SignalManager()
    sm.start()

    # Do some other stuff until someone presses Ctrl+C
    try:
        while True:
            time.sleep(5)
            sm.send("tic tac")

    except KeyboardInterrupt:
        # Shutdown client
        sm.stop()
