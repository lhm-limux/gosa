# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_service.py 1006 2010-09-30 12:43:58Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
import curses
import sys
import time
import gettext
from gosa.client.plugins.join.methods import join_method
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("gosa.client", "locale"), fallback=True)
_ = t.ugettext


class CursesGUI(join_method):
    priority = 90

    def __init__(self, parent=None):
        super(CursesGUI, self).__init__()

    def start_gui(self):
        self.screen = curses.initscr()

    def end_gui(self):
        curses.endwin()

    def get_pw(self):
        curses.noecho()
        curses.cbreak()
        password=""
        pos=0
        self.screen.move(11, 25 + pos)

        while 1:
            c = self.screen.getch()
            if c == 10:
                break
            elif c == 127:

                if (pos > 0):
                    pos = pos - 1

                self.screen.move(11, 25 + pos)
                self.screen.addch(" ")
                self.screen.move(11, 25 + pos)
                self.screen.refresh()
                password = password[0:len(password)-1]
            else:
                self.screen.move(11, 25 + pos)
                pos = pos + 1
                self.screen.addch("*")
                self.screen.refresh()
                password = password + chr(c)

        curses.nocbreak()
        curses.echo()

        return password

    def join_dialog(self):
        key = None
        self.start_gui()

        while not key:
            self.screen.border(0)
            self.screen.addstr(7, 14, _("Please enter username and password to join GOsa"))
            self.screen.addstr(8, 14, "(" + _("press Ctrl-C to cancel") + ")")
            self.screen.addstr(10, 14, _("Username") + ":")
            self.screen.addstr(11, 14, _("Password") + ":")
            self.screen.refresh()

            username = self.screen.getstr(10, 25, 16)
            password = self.get_pw()
            key = self.join(username, password)

        self.end_gui()

    def show_error(self, error):
        self.screen.addstr(13, 14, error)
        self.screen.refresh()
        time.sleep(3)
        self.screen.clear()

    @staticmethod
    def available():
        # No special needs for curses, just set us to True
        return True
