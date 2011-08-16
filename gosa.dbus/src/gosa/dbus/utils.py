# -*- coding: utf-8 -*-
import dbus.service
import dbus.mainloop.glib


def get_system_bus():
    """
    *get_system_bus* acts as a singleton and returns the
    system bus for 'com.gonicus.gosa'.

    ``Return:`` system bus
    """
    if not get_system_bus.bus:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        get_system_bus.bus = dbus.SystemBus()
        get_system_bus.name = dbus.service.BusName('com.gonicus.gosa', get_system_bus.bus)

    return get_system_bus.bus

get_system_bus.bus = None
