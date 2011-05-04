#!/usr/bin/env python
import gobject
import dbus
import dbus.glib
import dbus.mainloop.glib
from threading import Thread
from dateutil.parser import parse


class SeatKeeper(object):

    __sessions = {}
    active = False

    def __init__(self, callback=None):
        self.__callback = callback
        self.__bus = None
        self.__loop = None
        self.__thread = None

    def start(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.__bus = dbus.SystemBus()
        self.active = True

        def runner():
            self.__update_sessions()

            # register a signal receiver
            self.__bus.add_signal_receiver(self.event_handler,
                dbus_interface = "org.freedesktop.ConsoleKit.Seat",
                message_keyword='dbus_message')

            self.__loop = gobject.MainLoop()
            gobject.threads_init()
            dbus.glib.init_threads()
            context = gobject.MainLoop().get_context()

            while self.active:
                context.iteration(True)

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stop(self):
        self.active = False
        self.__loop.quit()
        self.__thread.join()

    def event_handler(self, msg_string, dbus_message):
        self.__update_sessions()
        if self.__callback:
            self.__callback(dbus_message.get_member(), msg_string)

    def __update_sessions(self):
        obj = self.__bus.get_object("org.freedesktop.ConsoleKit",
            "/org/freedesktop/ConsoleKit/Manager")
        sessions = {}

        for session_name in obj.GetSessions():
            session_o = self.__bus.get_object("org.freedesktop.ConsoleKit",
                session_name)

            sessions[str(session_name).split("/")[-1]] = {
                "uid": int(session_o.GetUser()),
                "active": bool(session_o.IsActive()),
                "created": parse(str(session_o.GetCreationTime())),
                "display": str(session_o.GetX11Display()),
            }

        self.__sessions = sessions

    def get_sessions(self):
        return self.__sessions



# Some class demo ---

def clbk(session, message):
    print "%s: %s" % (session, str(message).split("/")[-1])


if __name__ == '__main__':
    import time

    sm = SeatKeeper(callback=clbk)
    sm.start()

    try:
        a = None

        while True:
            time.sleep(1)
            b = sm.get_sessions()
            if a != b:
                a = b
                print "Session\t\tUID\tActive\tCreation time"
                print "-" * 80
                for sess, more in b.iteritems():
                    print "%s\t%s\t%s\t%s" % \
                        (sess, more['uid'], more['active'], more['created'])
                print

    except KeyboardInterrupt:
        sm.stop()
