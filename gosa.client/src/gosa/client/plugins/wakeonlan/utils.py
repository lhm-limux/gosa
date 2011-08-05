# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 612 2010-08-16 09:21:44Z cajus $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
import dbus
from gosa.common.components import Plugin
from gosa.common.components import Command
from gosa.common import Environment


class WakeOnLan(Plugin):
    """
    Utility class that contains methods needed to handle WakeOnLAN
    functionality.
    """
    _target_ = 'wakeonlan'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

    @Command()
    def wakeonlan(self, macaddr):
        """ Sent a WakeOnLAN paket to the given MAC address. """
        bus = dbus.SystemBus()
        gosa_dbus = bus.get_object('com.gonicus.gosa',
                                   '/com/gonicus/gosa/wol')
        return gosa_dbus.wakeOnLan(macaddr, dbus_interface="com.gonicus.gosa")
