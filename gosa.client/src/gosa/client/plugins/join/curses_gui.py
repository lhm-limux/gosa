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
	self.height, self.width = self.screen.getmaxyx()

        curses.start_color()

    def end_gui(self):
        curses.endwin()

    def get_pw(self):
        curses.noecho()
        curses.cbreak()
        password=""
        pos=0
        self.screen.move(self.start_y + 4, self.start_x + 11 + pos)

        while 1:
            c = self.screen.getch()
            if c == 10:
                break
            elif c == 127:

                if (pos > 0):
                    pos = pos - 1

                self.screen.move(self.start_y + 4, self.start_x + 11 + pos)
                self.screen.addch(" ")
                self.screen.move(self.start_y + 4, self.start_x + 11 + pos)
                self.screen.refresh()
                password = password[0:len(password)-1]
            else:
                self.screen.move(self.start_y + 4, self.start_x + 11 + pos)
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
	headline = _("Please enter the credentials of an administrative user to join this client.")
	self.start_x = (self.width - len(headline)) / 2 - 1
	self.start_y = self.height / 2 - 5

        while not key:
            self.screen.border(0)
            self.screen.addstr(self.start_y, self.start_x, headline)
            self.screen.addstr(self.start_y + 1, self.start_x, "(" + _("Press Ctrl-C to cancel") + ")")
            self.screen.addstr(self.start_y + 3, self.start_x, _("User name") + ":")
            self.screen.addstr(self.start_y + 4, self.start_x, _("Password") + ":")
            self.screen.refresh()

            username = self.screen.getstr(self.start_y + 3, self.start_x + 11, 16)
            password = self.get_pw()
            if not username or not password:
		self.show_error("Please enter a user name and a password!")
                continue
            key = self.join(username, password)

        self.end_gui()

    def show_error(self, error):
        self.screen.addstr(self.start_y + 6, self.start_x, error)
        self.screen.refresh()
        time.sleep(3)
        self.screen.clear()

    @staticmethod
    def available():
        # No special needs for curses, just set us to True
        return True