#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import dbus.service
from gosa.common.env import Environment
from gosa.common.components.plugin import Plugin
from gosa.dbus.utils import get_system_bus
import warnings
#warnings.filterwarnings("ignore")

import re
import sys
import grp
import pynotify
import gobject
import dbus
import dbus.mainloop.glib
import time
from optparse import OptionParser, OptionValueError
import pwd
import getpass


class DBusNotifyHandler(dbus.service.Object, Plugin):
    """ Notify handler, sends user notifications """

    def __init__(self):
        conn = get_system_bus()
        dbus.service.Object.__init__(self, conn, '/com/gonicus/gosa/notify')
        self.env = Environment.getInstance()

    @dbus.service.method('com.gonicus.gosa', in_signature='', out_signature='')
    def send(self, user):
        try:
            n = Notify()
            n.send_to_user('title', 'message', user)
        except Exception as inst:
            print inst
            print inst.args


# Define return codes
RETURN_ABORTED = 0b10000000
RETURN_TIMEDOUT = 0b1000000
RETURN_CLOSED_WITH_ACTION = 0b100000
RETURN_CLOSED = 0b10000
# 000 to 111 are selected action types.


class Notify(object):
    """
    Allows to send desktop notifications to users.
    """
    __actions = None
    __loop = None
    __recurrenceTime = 60

    def __init__(self):
        pynotify.init('gosa-ng')

    def __close_all(self):
        """
        Closes all opened notification windows.
        """
        for noti in self.__notify:
            noti.close()

    def __show_all(self):
        """
        Shows all notification windows.
        """
        for noti in self.__notify:
            noti.show()

    def __callback(self, notification=None, action=None):
        """
        __callback acts on notification actions, if actions were defined.
        """
        # Get the selected action id, the first is 0 so we just add +1 to it,
        # to get a more useable return code.
        self.__res = (self.__actions.index(action) + 1) | RETURN_CLOSED_WITH_ACTION
        self.__close_all()
        self.__loop.quit()

    def notification_closed(self, *args, **kwargs):
        """
        notification_closed is called whenever a notification is closed
        If no action was selected from the given ones, then show the
        notification again.
        """
        # Is there a valid result selected? If not, then show the dialog again.
        if self.__actions and self.__res == -1:
            try:
                time.sleep(self.__recurrenceTime)
                self.__show_all()
            except KeyboardInterrupt:
                self.__res = RETURN_ABORTED
                self.__close_all()
                self.__loop.quit()
        else:
            self.__loop.quit()

    def send(self, title, message, icon="dialog-information",
        urgency=pynotify.URGENCY_NORMAL,
        timeout=pynotify.EXPIRES_DEFAULT,
        recurrence=60,
        dbus_sessions=[],
        **kwargs):
        """
        send    initiates the notification with the given option details.
        If actions were specified then it hooks in the MainLoop to keep
        the programm running till an action was selected or the programm
        was interrupted.
        """

        # Initially start with result id 0 for non-action notificatiuons
        #  and with 255 for action notifications.
        self.__res = -1

        # If a list of dbus session addresses was given then
        #  initiate a notification for each.
        self.__notify = []
        if dbus_sessions:
            for dbus_sess in dbus_sessions:

                # Set DBUS address in the environment
                os.environ['DBUS_SESSION_BUS_ADDRESS'] = dbus_sess

                # Build dialog
                notify = pynotify.Notification(title, message, icon)
                self.__notify.append(notify)

                # Set up notification details like actions
                notify.set_urgency(urgency)
                if 'actions' in kwargs:
                    notify.set_timeout(pynotify.EXPIRES_NEVER)
                    self.__recurrenceTime = recurrence
                    self.__actions = kwargs['actions']
                    for action in kwargs['actions']:
                        notify.add_action(action, action, self.__callback)
                else:
                    notify.set_timeout(timeout)

            # Display all created notifications
            self.__show_all()

        else:

            print "Requires at least one DBUS address"
            return

        # Register provided actions and then hook in the main loop
        if not self.__actions:
            self.__res = RETURN_CLOSED
        else:

            # Register callback for 'NotificationClosed' event on the dbus.
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            bus.add_signal_receiver(self.notification_closed,
                dbus_interface="org.freedesktop.Notifications", signal_name="NotificationClosed")

            # Hook in the main loop, to keep the programm running till an action
            # was selected or the application was closed.
            self.__loop = gobject.MainLoop()
            try:
                self.__loop.run()
            except KeyboardInterrupt:
                try:
                    self.__close_all()
                except gobject.GError:
                    pass
                self.__res = RETURN_ABORTED

        return self.__res

    def send_to_user(self, title, message, user,
        icon="dialog-information",
        actions=[],
        urgency=pynotify.URGENCY_NORMAL,
        timeout=pynotify.EXPIRES_DEFAULT,
        recurrence=60, **kwargs):

        """
        Sends a notification message to a given user.
        """

        # Use current user if none was given
        if not user:
            user = getpass.getuser()

        # Send the notification to each found dbus address
        dbus_sessions = self.getDBUSAddressesForUser(user)
        res = None
        if not dbus_sessions:
            print "No DBUS sessions found for user " + user
            res = RETURN_ABORTED
        else:

            # Detecting groups of user options.user
            gids = []
            for agrp in grp.getgrall():
                if user in agrp.gr_mem:
                    gids.append(agrp.gr_gid)

            # Now Switch to the selected user, primary group und uid
            #  for the current os environment
            info = pwd.getpwnam(user)

            # Set the users groups
            if os.geteuid() != info[2]:
                os.setgroups(gids)
                os.setgid(info[3])
                os.seteuid(info[2])

            # Fork a new process to send the notification
            parent_pid = os.getpid()
            child_pid = os.fork()

            # Call the send method in the fork only
            if child_pid == 0:

                # Try to send the notification now.
                res = self.send(title, message, actions=actions, icon=icon,
                    urgency=urgency, timeout=timeout, recurrence=recurrence,
                    dbus_sessions=dbus_sessions)

                # Exit the cild process
                sys.exit(res)
            else:

                # Get the cild process return code.
                (pid, ret_code) = os.waitpid(child_pid, 0)

                # Dont know why, but we receive an 16 Bit long return code,
                # but only send an 8 Bit value.
                res = ret_code >> 8

        return res

    def getDBUSAddressesForUser(self, user):
        """
        Searches the process list for a DBUS Sessions that were opened by
        the given user, the found DBUS addresses will be returned
        """

        # Prepare regular expressions to find processes for X sessions
        prog = re.compile("(gnome-session|x-session-manager|/bin/sh.*/usr/bin/startkde)")

        # Walk through process ids and search for processes owned by 'user'
        #  which represents a X Session.
        dbusAddresses = []
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
        for pid in pids:

            # Get the command line statement for the process and check if it represents
            #  an X Session.
            cmdline = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            if prog.match(cmdline) and user == pwd.getpwuid(os.stat(os.path.join('/proc', pid, 'cmdline')).st_uid).pw_name:

                # Extract the DBUS Session address, to be able to connect to it later.
                environment = open(os.path.join('/proc', pid, 'environ'), 'rb').read()
                m = re.search('^.*DBUS_SESSION_BUS_ADDRESS=([^\0]*).*$', environment + "test")
                if m.group(1):
                    dbusAddresses.append(m.group(1))

        return dbusAddresses


def checkUrgency(option, opt, value, parser):
    """
    checkUrgency    checks whether the given value for the urgency option
    is valid or not and then updates the cli-option-parser
    It defaults to pynotify.URGENCY_NORMAL.
    """

    # Create a dictionary for all valid values.
    attrMap = {}
    attrMap[None] = pynotify.URGENCY_NORMAL
    attrMap['critical'] = pynotify.URGENCY_CRITICAL
    attrMap['normal'] = pynotify.URGENCY_NORMAL
    attrMap['low'] = pynotify.URGENCY_LOW

    # If a invalid value was specified, then tell the user and default to normal.
    if value not in attrMap:
        value = None
        raise OptionValueError("Invalid urgency level specified. (critical, normal, low)")

    # Update the cli-option-parser now.
    parser.values.urgency = value

if __name__ == '__main__':
    n = Notify()

    # Define cli-script parameters
    parser = OptionParser(description="Sends a notification dialog "
        "to a user on the local machine.",
        prog="notify", usage="%prog <message> <title> [options] ")

    parser.add_option("-l", "--urgency", type="string", help="Urgency level",
        callback=checkUrgency, action="callback", default=pynotify.URGENCY_NORMAL)
    parser.add_option("-i", "--icon", dest="icon",
        help="An icon file to use in the notifcation", metavar="FILE")
    parser.add_option("-t", "--timeout", dest="timeout",
        help="Milliseconds the notification is displayed")
    parser.add_option("-u", "--user", dest="user", help="The target user")
    parser.add_option("-q", "--quiet", action="store_false", dest="verbose",
        default=True, help="don't print status messages to stdout")
    parser.add_option("-a", "--actions", dest="actions",
        help="A list of actions the notification is displayed. E.g. -a 'yes,no'")
    parser.add_option("-r", "--recurrence-time", dest="recurrence", type="float",
        help="Recurrence time of unanswered actions notifications.", default=60)

    # Check if at least 'message' and 'title' are given.
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
    else:

        # Prepare actions
        actions = []
        if options.actions:
            actions = options.actions.split(',')

        # Check if actions and timeout are given, timeout will be ignored in this case.
        if options.actions and options.timeout and options.verbose:
            print "The options 'timeout' and 'actions' cannot be combined, timeout will be ingored!"

        # Ensure that the timeout is valid
        if options.timeout:
            options.timeout = int(options.timeout)
        else:
            options.timeout = pynotify.EXPIRES_DEFAULT

        # Call the send method for our notification instance
        sys.exit(n.send_to_user(args[0], args[1], user=options.user, actions=actions, icon=options.icon,
            urgency=options.urgency, timeout=options.timeout, recurrence=options.recurrence))


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
