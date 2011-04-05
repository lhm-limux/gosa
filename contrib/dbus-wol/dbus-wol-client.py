#!/usr/bin/env python2.6

import dbus
bus = dbus.SystemBus()
gosa_dbus = bus.get_object('com.gonicus.gosa',
                      '/com/gonicus/gosa/object')
#ret = eth0.getProperties(dbus_interface='org.freedesktop.NetworkManager.Devices')
ret = gosa_dbus.wakeOnLan('00:26:2d:f2:aa:36', dbus_interface = "com.gonicus.gosa")
print "return code:", ret
