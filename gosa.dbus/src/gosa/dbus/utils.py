# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 869 2010-09-07 08:04:08Z cajus $$

 See LICENSE for more information about the licensing.
"""
import dbus.service
import dbus.mainloop.glib

def get_system_bus():
    if not get_system_bus.bus:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        get_system_bus.bus = dbus.SystemBus()
        get_system_bus.name = dbus.service.BusName('com.gonicus.gosa', get_system_bus.bus)

    return get_system_bus.bus

get_system_bus.bus = None
