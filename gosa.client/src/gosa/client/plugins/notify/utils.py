# -*- coding: utf-8 -*-
import dbus
from gosa.common.components import Plugin
from gosa.common.components import Command
from gosa.common import Environment


class Notify(Plugin):
    """
    Utility class that contains methods needed to handle WakeOnLAN
    notification functionality.
    """
    _target_ = 'notify'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

    @Command()
    def notify(self, user, title, message,
        timeout=0,
        urgency="normal",
        icon="dialog-information",
        actions="",
        recurrence=60):

        """ Sent a notification to a given user """

        # Get BUS connection
        bus = dbus.SystemBus()
        gosa_dbus = bus.get_object('com.gonicus.gosa',
                                   '/com/gonicus/gosa/notify')

        # Send notification and keep return code
        o = gosa_dbus.notify(user, title, message, timeout, urgency,
            icon, actions, recurrence, dbus_interface="com.gonicus.gosa")
        return(int(o))

    @Command()
    def notify_all(self, title, message,
        timeout=0,
        urgency="normal",
        icon="dialog-information",
        actions="",
        recurrence=60):

        """ Sent a notification to all users on a machine """

        # Get BUS connection
        bus = dbus.SystemBus()
        gosa_dbus = bus.get_object('com.gonicus.gosa',
                                   '/com/gonicus/gosa/notify')

        # Send notification and keep return code
        o = gosa_dbus.notify_all(title, message, timeout, urgency,
            icon, actions, recurrence, dbus_interface="com.gonicus.gosa")
        return(int(o))
