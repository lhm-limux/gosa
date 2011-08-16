import dbus.service
import subprocess
from gosa.common import Environment
from gosa.common.components import Plugin
from gosa.dbus import get_system_bus


class DBusWakeOnLanHandler(dbus.service.Object, Plugin):
    """ WOL handler, exporting shell commands to the bus """

    def __init__(self):
        conn = get_system_bus()
        dbus.service.Object.__init__(self, conn, '/com/gonicus/gosa/wol')
        self.env = Environment.getInstance()

    @dbus.service.method('com.gonicus.gosa', in_signature='s', out_signature='')
    def wakeOnLan(self, mac):
        p = subprocess.Popen([r"wakeonlan", mac])
        p.wait()
        # return exit code, unfortunately wakeonlan returns 0
        # even when an error occurs :(
        return p.returncode
