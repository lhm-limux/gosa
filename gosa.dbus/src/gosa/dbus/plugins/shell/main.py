import os
import dbus.service
from gosa.common.env import Environment
from gosa.common.components.plugin import Plugin
from gosa.dbus.utils import get_system_bus


class DBusShellHandler(dbus.service.Object, Plugin):
    """ Shell handler, exporting shell commands to the bus """

    def __init__(self):
        conn = get_system_bus()
        dbus.service.Object.__init__(self, conn, '/com/gonicus/gosa/shell')
        self.env = Environment.getInstance()

    @dbus.service.method('com.gonicus.gosa', in_signature='', out_signature='')
    def get_signatures(self):
        pass
