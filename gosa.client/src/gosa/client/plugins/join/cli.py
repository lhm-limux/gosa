# -*- coding: utf-8 -*-
import time
import gettext
import getpass
from gosa.client.plugins.join.methods import join_method
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("gosa.client", "locale"), fallback=True)
_ = t.ugettext


class Cli(join_method):
    priority = 99

    def __init__(self, parent=None):
        super(Cli, self).__init__()

    def join_dialog(self):
        key = None

        while not key:
            print(_("Please enter username and password to join GOsa"))
            username = raw_input(_("User name [%s]: ") % getpass.getuser())
            password = getpass.getpass(_("Password") + ": ")
            key = self.join(username, password)

    def show_error(self, error):
        print(_("Error") + ": " + error)
        time.sleep(3)

    @staticmethod
    def available():
        # This should always work
        return True
