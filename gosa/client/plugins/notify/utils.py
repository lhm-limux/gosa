# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 612 2010-08-16 09:21:44Z cajus $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
import dbus
from gosa.common.components.plugin import Plugin
from gosa.common.components.command import Command
from gosa.common.env import Environment


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
    def notify(self, title, message, user,
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
        o = gosa_dbus.notify(title, message, user, timeout, urgency,
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
