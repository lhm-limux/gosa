# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 313 2010-07-06 16:37:18Z sommer $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
import dbus
from gosa.common.components.plugin import Plugin
from gosa.common.components.command import Command
from gosa.common.env import Environment


class PowerManagement(Plugin):
    """
    Utility class that contains methods needed to handle shutdown 
    functionality.
    """
    _target_ = 'powermanagement'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

    @Command()
    def shutdown(self):
        """ Execute a shutdown of the client. """
        bus = dbus.SystemBus()
        hal_dbus = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
        hal_dbus.Shutdown(dbus_interface="org.freedesktop.Hal.Device.SystemPowerManagement")

        return True

    @Command()
    def reboot(self):
        """ Execute a reboot of the client. """
        bus = dbus.SystemBus()
        hal_dbus = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
        hal_dbus.Reboot(dbus_interface="org.freedesktop.Hal.Device.SystemPowerManagement")

        return True

    @Command()
    def suspend(self):
        """ Execute a suspend of the client. """
        bus = dbus.SystemBus()
        hal_dbus = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
        hal_dbus.Suspend(dbus_interface="org.freedesktop.Hal.Device.SystemPowerManagement")

        return True

    @Command()
    def hibernate(self):
        """ Execute a hibernation of the client. """
        bus = dbus.SystemBus()
        hal_dbus = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
        hal_dbus.Hibernate(dbus_interface="org.freedesktop.Hal.Device.SystemPowerManagement")

        return True

    @Command()
    def setpowersave(self, enable):
        """ Set powersave mode of the client. """
        bus = dbus.SystemBus()
        hal_dbus = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
        hal_dbus.SetPowerSave(enable, dbus_interface="org.freedesktop.Hal.Device.SystemPowerManagement")

        return True

