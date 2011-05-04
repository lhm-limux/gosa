# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 612 2010-08-16 09:21:44Z cajus $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
import gobject
import dbus
import pwd
import dbus.glib
import dbus.mainloop.glib
from threading import Thread
from dateutil.parser import parse
from gosa.common.components.plugin import Plugin
from gosa.common.components.command import Command
from gosa.common.env import Environment


class SessionKeeper(Plugin):
    """
    Utility class that contains methods needed to handle WakeOnLAN
    functionality.
    """
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
        self.start()

    def __del__(self):
        self.stop()

    @Command()
    def getSessions(self):
        """ Return the list of active sessions """
        return self.__sessions

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

            uid = pwd.getpwuid(int(session_o.GetUser())).pw_name
            sessions[str(session_name).split("/")[-1]] = {
                "uid": uid,
                "active": bool(session_o.IsActive()),
                "created": parse(str(session_o.GetCreationTime())),
                "display": str(session_o.GetX11Display()),
            }

        self.__sessions = sessions
