# -*- coding: utf-8 -*-
import gobject
import pwd
import dbus.glib
import dbus.mainloop.glib
from threading import Thread
from dateutil.parser import parse
from gosa.common.components import Plugin
from gosa.common.components import Command
from gosa.common.components.registry import PluginRegistry
from gosa.common import Environment
from gosa.common.event import EventMaker
from zope.interface import implements
from gosa.common.handler import IInterfaceHandler
import time


class SessionKeeper(Plugin):
    """
    Utility class that contains methods needed to handle WakeOnLAN
    functionality.
    """
    implements(IInterfaceHandler)
    _priority_ = 99
    _target_ = 'session'
    __sessions = {}
    __callback = None
    active = False

    def __init__(self):
        env = Environment.getInstance()
        self.env = env
        self.__bus = None
        self.__loop = None
        self.__thread = None

    @Command()
    def getSessions(self):
        """ Return the list of active sessions """
        return self.__sessions

    def serve(self):
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
                context.iteration(False)
                if not context.pending():
                    time.sleep(1)

        self.__thread = Thread(target=runner)
        self.__thread.start()

    def stop(self):
        self.active = False
        self.__loop.quit()
        self.__thread.join()

    def event_handler(self, msg_string, dbus_message):
        self.__update_sessions()

        if self.__callback:
            #pylint: disable=E1102
            self.__callback(dbus_message.get_member(), msg_string)

    def __update_sessions(self):
        obj = self.__bus.get_object("org.freedesktop.ConsoleKit",
            "/org/freedesktop/ConsoleKit/Manager")
        sessions = {}

        for session_name in obj.GetSessions():
            session_o = self.__bus.get_object("org.freedesktop.ConsoleKit",
                session_name)

            uid = pwd.getpwuid(int(session_o.GetUser())).pw_name
            sessions[str(session_name).split("/")[-1]] = {
                "uid": uid,
                "active": bool(session_o.IsActive()),
                "created": parse(str(session_o.GetCreationTime())),
                "display": str(session_o.GetX11Display()),
            }

        self.__sessions = sessions
        self.sendSessionNotification()

    def sendSessionNotification(self):
        # Build event
        amqp = PluginRegistry.getInstance("AMQPClientHandler")
        e = EventMaker()
        more = set([x['uid'] for x in self.__sessions.values()])
        more = map(e.Name, more)
        info = e.Event(
            e.UserSession(
                e.Id(self.env.uuid),
		e.User(*more)))

        amqp.sendEvent(info)
