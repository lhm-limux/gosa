#!/usr/bin/env python2.6


import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

import subprocess


# object, which is exported to dbus
class TestObject(dbus.service.Object):
    def __init__(self, conn, object_path='/com/gonicus/gosa/object'):
        dbus.service.Object.__init__(self, conn, object_path)

    @dbus.service.method('com.gonicus.gosa', in_signature='s', out_signature='i')
    def wakeOnLan(self, macAddr):
	p = subprocess.Popen([r"wakeonlan",macAddr])
	p.wait()
	# return exit code, unfortunately wakeonlan returns 0 
	# even when an error occurs :(
        return p.returncode

    @dbus.service.method("com.gonicus.gosa", in_signature='', out_signature='')
    def Exit(self):
        loop.quit()


# connect to dbus and setup loop
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    system_bus = dbus.SystemBus()
    name = dbus.service.BusName('com.gonicus.gosa', system_bus)
    object = TestObject(system_bus)

    loop = gobject.MainLoop()
    loop.run()
