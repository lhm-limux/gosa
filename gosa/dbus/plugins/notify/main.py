#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import warnings
#warnings.filterwarnings("ignore")

import os
import dbus.service
from gosa.common.env import Environment
from gosa.common.components.plugin import Plugin
from gosa.dbus.utils import get_system_bus
import sys
import traceback
import subprocess

class DBusNotifyHandler(dbus.service.Object, Plugin):
    """ Notify handler, sends user notifications """

    def __init__(self):
        conn = get_system_bus()
        dbus.service.Object.__init__(self, conn, '/com/gonicus/gosa/notify')
        self.env = Environment.getInstance()

    @dbus.service.method('com.gonicus.gosa', in_signature='', out_signature='')
    def send(self, message, title, user,
        timeout="",
        actions="",
        urgency="",
        icon="",
        recurrence=""):
        """
        Try to send a notification to a user using the 'notify-user' script.
        """

        try:

            # Build up the subprocess command 
            # and add parameters on demand.
            cmd = ["notify-user"]
            cmd += [str(title)]
            cmd += [str(message)]
            cmd += ["--user"]
            cmd += [str(user)]

            if icon:
                cmd += ["--icon"]
                cmd += [str(icon)]
       
            if actions: 
                cmd += ["--actions"]
                cmd += [str(actions)]
            
            if urgency:
                cmd += ["--urgency"]
                cmd += [str(urgency)]

            if timeout:
                cmd += ["--timeout"]
                cmd += [str(timeout)]

            if recurrence:
                cmd += ["--recurrence"]
                cmd += [str(recurrence)]

            return subprocess.Popen(cmd)
        except Exception as inst:
            traceback.print_exc(file=sys.stdout)

