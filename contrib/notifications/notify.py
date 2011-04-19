#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import pynotify
import gobject


class Notify(object):
    __actions = None

    def __init__(self):
        pynotify.init('gosa-ng')

    def __callback(self, notification=None, action=None, data=None):
        self.__res = self.__actions.index(data)
        self.loop.quit()

    def send(self, title, message, icon="dialog-information",
        urgency=pynotify.URGENCY_NORMAL,
        timeout=pynotify.EXPIRES_DEFAULT, **kwargs):

        self.__res = 0

        # Build dialog
        notify = pynotify.Notification(title, message, icon)

        # Set up actions - here we want an answer, ignore
        # timeout.
        if 'actions' in kwargs:
            timeout = pynotify.EXPIRES_NEVER
            self.__actions = kwargs['actions']
            for action in kwargs['actions']:
                notify.add_action(action, action, self.__callback, action)

        notify.set_timeout(timeout)
        notify.set_urgency(urgency)
        notify.show()

        if self.__actions:
            self.loop = gobject.MainLoop()
            try:
                self.loop.run()
            except KeyboardInterrupt:
                pass

        return self.__res


if __name__=='__main__':
    n = Notify()
    sys.exit(n.send("Ottfried on the run", "Hallo Welt!", actions=['Ja', 'Nein']))
#sys.exit(n.send("Ottfried on the run", "Hallo Welt!",))


###############################################
# Usecases:
#
# 1) Simple Nachricht
#    Timeout, Titel, Nachricht (HTML), Icon, Urgency (low, normal, critical)
#
#    Timeout:
#    EXPIRES_DEFAULT = -1
#    EXPIRES_NEVER = 0
#
#    Urgency:
#    URGENCY_CRITICAL
#    URGENCY_LOW
#    URGENCY_NORMAL
#
#    Icon (z.B.):
#    dialog-information
#    dialog-warning
#    dialog-error
#    dialog-question
#
# 2) Nachricht mit Callbacks
#    Timeout (mandatory), Titel, Nachricht (HTML), Icon, Urgency (low, normal, critical)
#    "Button 1", "Button 2", ...
#    
#    -> wartet auf bestätigung, max. timeout -> -1
