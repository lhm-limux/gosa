#!/usr/bin/env python
# -*- coding: utf-8 -*-
import warnings
warnings.filterwarnings("ignore")

import os
import re
import sys
import grp
import pynotify
import gobject
import dbus.mainloop.glib
import time
from optparse import OptionParser, OptionValueError
import pwd
import getpass
import signal

# Define return codes
RETURN_ABORTED = 0b10000000
RETURN_TIMEDOUT = 0b1000000
RETURN_CLOSED = 0b0

class Notify(object):
    """
    Allows to send desktop notifications to users.
    """
    __actions = None
    __loop = None
    __recurrenceTime = 60
    quiet = False
    verbose = False
    children = []

    def __init__(self, quiet=False, verbose=False):
        pynotify.init('gosa-ng')
        self.quiet = quiet
        self.verbose = verbose

    def __callback(self, notification=None, action=None):
        """
        __callback acts on notification actions, if actions were defined.
        """
        # Get the selected action id, the first is 0 so we just add +1 to it,
        # to get a more useable return code.
        self.__res = (self.__actions.index(action) + 1) | RETURN_CLOSED

        if self.verbose:
            print "%s: Action selected (%s) " % (str(os.getpid()), str(action))

        self.__close()

    def __close(self, *args, **kwargs):

        """
        Closes the corrent show notification and its mainloop if it exists.
        """
        if self.verbose:
            print "%s: Closing" % (str(os.getpid()))

        if self.__notify:
            self.__notify.close()

        if self.__loop:
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
                if self.verbose:
                    print "%s: Notification was avoided, showing it again in (%s) second" % (
                        str(os.getpid()), str(self.__recurrenceTime))

                time.sleep(self.__recurrenceTime)
                self.__notify.show()
            except KeyboardInterrupt:

                if self.verbose:
                    print "%s: Keyboard interrupt. CLOSING" % (str(os.getpid()))

                self.__res = RETURN_ABORTED
                self.__close()

        else:
            self.__loop.quit()

    def send(self, title, message, dbus_session,
        icon="dialog-information",
        urgency=pynotify.URGENCY_NORMAL,
        timeout=pynotify.EXPIRES_DEFAULT,
        recurrence=60,
        actions=[],
        **kwargs):
        """
        send    initiates the notification with the given option details.
        If actions were specified then it hooks in the MainLoop to keep
        the programm running till an action was selected or the programm
        was interrupted.
        """

        # Keep 'actions' value to be able to act on callbacks later
        self.__actions = actions

        # Prepare timeout, use seconds not milliseconds
        if timeout != pynotify.EXPIRES_DEFAULT:
            timeout *= 1000

        # Initially start with result id -1
        self.__res = -1

        # If a list of dbus session addresses was given then
        #  initiate a notification for each.
        if not dbus_session:

            # No dbus session was specified, abort here.
            if not self.quiet:
                print "Requires a DBUS address to send notifications"

            return(RETURN_ABORTED)

        else:

            # Set DBUS address in the environment
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = dbus_session

            # Build notification
            notify = pynotify.Notification(title, message, icon)

            # Set up notification details like actions
            notify.set_urgency(urgency)
            if actions:
                notify.set_timeout(pynotify.EXPIRES_NEVER)
                self.__recurrenceTime = recurrence
                for action in actions:
                    notify.add_action(action, action, self.__callback)
            else:
                notify.set_timeout(timeout)

            # Display all created notifications
            self.__notify = notify
            self.__notify.show()

        # Register provided actions and then hook in the main loop
        if not actions:
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
                self.__res = RETURN_ABORTED
                self.__close()

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
            if not self.quiet:
                print "No DBUS sessions found for user " + user

            res = RETURN_ABORTED
        else:

            # Walk through found dbus sessions and fork a process for each
            parent_pid = os.getpid()
            self.children = []
            for use_user in dbus_sessions:
                for d_session in dbus_sessions[use_user]:

                    # Some verbose output
                    if self.verbose:
                        print "\nInitiating notifications for user: %s" % use_user
                        print "Session: %s" % d_session

                    # Detecting groups for user
                    gids = []
                    for agrp in grp.getgrall():
                        if use_user in agrp.gr_mem:
                            gids.append(agrp.gr_gid)

                    # Get system information for the user
                    info = pwd.getpwnam(use_user)

                    # Fork a new sub-process to be able to set the user details
                    # in a save way, the parent should not be affected by this.
                    child_pid = os.fork()

                    # Call the send method in the fork only
                    if child_pid == 0:

                        if self.verbose:
                            print "%s: Forking process for user %s" % (str(os.getpid()), str(info[2]))

                        # Set the users groups
                        if os.geteuid() != info[2]:
                            os.setgroups(gids)
                            os.setgid(info[3])
                            os.seteuid(info[2])

                        # Act on termniation events this process receives,
                        #  by closing the main loop and the notification window.
                        signal.signal(signal.SIGTERM, self.__close)

                        if self.verbose:
                            print "%s: Setting process uid(%s), gid(%s) and groups(%s)" % (
                                str(os.getpid()), str(info[2]), str(info[3]), str(gids))

                        # Try to send the notification now.
                        res = self.send(title, message, actions=actions, icon=icon,
                            urgency=urgency, timeout=timeout, recurrence=recurrence,
                            dbus_session=d_session)

                        # Exit the cild process
                        sys.exit(res)
                    else:
                        self.children.append(child_pid)

            # Wait for first child returning with an return code.
            if os.getpid() == parent_pid:

                try:
                    # Get the cild process return code.
                    (cpid, ret_code) = os.waitpid(-1, 0)

                    # Dont know why, but we receive an 16 Bit long return code,
                    # but only send an 8 Bit value.
                    res = ret_code >> 8

                except KeyboardInterrupt:
                    res = RETURN_ABORTED
                    pass

                # Now kill all remaining children
                for pid in self.children:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        if self.verbose:
                            print "Killed process %s" % pid
                    except Exception:
                        pass

        return res

    def getDBUSAddressesForUser(self, user):
        """
        Searches the process list for a DBUS Sessions that were opened by
        the given user, the found DBUS addresses will be returned in a dictionary
        indexed by the username.
        """

        # Prepare regular expressions to find processes for X sessions
        prog = re.compile("(gnome-session|x-session-manager|/bin/sh.*/usr/bin/startkde)")

        # Walk through process ids and search for processes owned by 'user'
        #  which represents a X Session.
        dbusAddresses = {}
        pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
        for pid in pids:

            # Get the command line statement for the process and check if it represents
            #  an X Session.
            cmdline = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            if prog.match(cmdline) and (user == '*' or
                    user == pwd.getpwuid(os.stat(os.path.join('/proc', pid, 'cmdline')).st_uid).pw_name):

                # Extract user name from running DBUS session
                dbus_user = pwd.getpwuid(os.stat(os.path.join('/proc', pid, 'cmdline')).st_uid).pw_name

                # Extract the DBUS Session address, to be able to connect to it later.
                environment = open(os.path.join('/proc', pid, 'environ'), 'rb').read()
                m = re.search('^.*DBUS_SESSION_BUS_ADDRESS=([^\0]*).*$', environment + "test")
                if m.group(1):

                    # Append the new dbus session to list of sessions found for the user
                    if dbus_user not in dbusAddresses:
                        dbusAddresses[dbus_user] = []

                    dbusAddresses[dbus_user].append(m.group(1))

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
        print OptionValueError("Invalid urgency level specified. (critical, normal, low)")
        sys.exit(RETURN_ABORTED)

    # Update the cli-option-parser now.
    parser.values.urgency = value


def main():

    # Define cli-script parameters
    parser = OptionParser(description="Sends a notification dialog "
        "to a user on the local machine.",
        prog="notify", usage="%prog <title> <message> [options] ")

    parser.add_option("-l", "--urgency", type="string", help="Urgency level",
        callback=checkUrgency, action="callback", default=pynotify.URGENCY_NORMAL)
    parser.add_option("-i", "--icon", dest="icon", default="dialog-information",
        help="An icon file to use in the notifcation", metavar="FILE")
    parser.add_option("-t", "--timeout", dest="timeout",
        help="Seconds the notification is displayed")
    parser.add_option("-u", "--user", dest="user", help="The target user")
    parser.add_option("-b", "--broadcast", action="store_true", dest="to_all",
        default=False, help="send message to all users")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
        default=False, help="don't print status messages to stdout")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
        default=False, help="Run in verbose mode")
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
        if options.actions and options.timeout and not options.quiet:
            print "The options 'timeout' and 'actions' cannot be combined, timeout will be ingored!"

        # Check if we've to send the message to all users instead of just one.
        if options.to_all:

            # Check if --user/-u was specified additionally.
            if options.user and not options.quiet:
                print "The option -b/--broadcast cannot be combined with the option -u/--user"

            options.user = "*"

        # If verbose output is enabled, then disable quiet mode.
        if options.verbose:
            options.quiet = False

        # Ensure that the timeout is valid
        if options.timeout:
            options.timeout = int(options.timeout)
        else:
            options.timeout = pynotify.EXPIRES_DEFAULT

        # Create notifcation object
        n = Notify(options.quiet, options.verbose)

        # Call the send method for our notification instance
        sys.exit(n.send_to_user(args[0], args[1], user=options.user, actions=actions, icon=options.icon,
            urgency=options.urgency, timeout=options.timeout, recurrence=options.recurrence))


if __name__ == '__main__':
    main()
