#!/usr/bin/env python
import sys
import traceback
import gobject
import dbus
import dbus.mainloop.glib


def signal_handler(message):
    print "[recieved]", message 


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    try:
        object  = bus.get_object("org.example.test",
		"/org/example/test/TestObject/object")
        object.connect_to_signal("HelloSignal",
		signal_handler,
		dbus_interface="org.example.test")

    except dbus.DBusException:
        traceback.print_exc()
        sys.exit(1)

    loop = gobject.MainLoop()
    loop.run()
