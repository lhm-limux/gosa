#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: main.py 1357 2010-11-15 09:12:54Z cajus $$

 See LICENSE for more information about the licensing.

 There are three usage scenarios:

 1) Interactive: Let's you execute code interactively.

     Usage:
       gosa-shell [-u/--user username] [-p/--password passwort]
           [service-uri]

 2) One-Shot: Executes code1...code2 and returns.

     Usage:
        gosa-shell [-u/--user username] [-p/--password passwort]
            [-c/--command 'cmd;cmd;...'] [service-uri]

 3) Script: Write a script and execute it.

     Usage:
        cat YourScript | gosa-shell [-u/--user username]
            [-p/--password passwort] [service-uri]

 The code you can execute is basically Python code. There is a special object
 named "gosa" that gives you access to all supported GOSA services. Try
 gosa.help() for a list of methods.
"""
from __future__ import print_function
import sys
import traceback
import code
import getopt
import socket
import getpass
#pylint: disable=W0611
import readline
import gettext
import textwrap
import locale
import thread
from types import ListType
from urllib2 import HTTPError
from pkg_resources import resource_filename
from dbus.exceptions import DBusException

from gosa.common.components import AMQPServiceProxy
from gosa.common.components import JSONServiceProxy, JSONRPCException
from gosa.common.components.zeroconf_client import ZeroconfClient
from gosa.common.utils import parseURL

# Set locale domain
t = gettext.translation('messages', resource_filename("gosa.shell", "locale"), fallback=True)
_ = t.ugettext


# Global lock
a_lock = thread.allocate_lock()


def softspace(fn, newvalue):
    """ Method copied from imported code """
    oldvalue = 0
    try:
        oldvalue = fn.softspace
    except AttributeError:
        pass
    try:
        fn.softspace = newvalue
    except (AttributeError, TypeError):
        # "attribute-less object" or "read-only attributes"
        pass
    return oldvalue


class MyConsole(code.InteractiveConsole):
    """ MyConsole Subclass of code.InteractiveConsole """

    # Stores the last code executed.
    lastCode = None

    def getLastCode(self):
        """ Put the last executed code object"""
        return self.lastCode

    def runcode(self, code):
        """
        Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.
        """
        self.lastCode = code
        try:
            exec code in self.locals
        except SystemExit:
            raise
        except HTTPError as e:
            if e.code == 401:
                raise
            self.showtraceback()
        except JSONRPCException as e:
            # Check for error member
            try:
                err = e.error["error"]
            except KeyError:
                err = str(e)
            if isinstance(err, ListType):
                print(err[0] % tuple(err[1:]))
            else:
                print(err.capitalize())
            if softspace(sys.stdout, 0):
                print()
        except Exception as e:
            #pylint: disable=W0612
            exc_type, exc_obj, exc_tb = sys.exc_info()
            self.showtraceback()
        else:
            if softspace(sys.stdout, 0):
                print()


class GOsaService():
    """ The GOsaService class encapsulates all GOSA functionality that is
        accessible via the interactive console. """
    proxy = None

    def __init__(self):
        self.name = 'GOsaService'
        self.domain = socket.getfqdn().split('.', 1)[1]

    def connect(self, service_uri='', username='', password=''):
        """ Creates a service proxy object from the arguments. """

        # Clean arguments
        username = username.strip()
        password = password.strip()
        service_uri = service_uri.strip()

        if len(service_uri) <= 0:
            print(_("Searching service provider..."))
            try:
                service_uri = ZeroconfClient.discover(['_amqps._tcp', '_amqp._tcp',
                    '_https._tcp', '_http._tcp'], domain=self.domain)[0]

            except DBusException as e:
                print(_("DBUS error: %s") % str(e))
                sys.exit(1)

            except Exception as e:
                print(e.__dict__)

        # Test if one argument is still needed.
        if len(service_uri) <= 0:
            tmp = service_uri
            service_uri = raw_input('Service URI: [%s]' % service_uri).strip()
            if len(service_uri) <= 0:
                service_uri = tmp

        # Chek if URL is parsable
        url = parseURL(service_uri)

        # If we have still no service host, quit, because the connect will fail
        # pylint: disable-msg=E1101
        if not url:
            print(_("Need at least a service URI!"))
            sys.exit(1)

        # TRANSLATOR: Conected to URL, i.e. https://amqp.local:8080/rpc
        print(_("Connected to %s://%s:%s/%s") %
            (url['scheme'], url['host'], url['port'], url['path']))

        # Check weather to use method parameters or the URI elements.
        # If URI username is set and the method username is not set
        if url['user']:
            username = url['user']
        # If URI password is set and the username is set and the method password is not set
        if url['password']:
            password = url['password']

        # If we have still no credentials query for them
        if len(username) <= 0:
            # TRANSLATOR: This is a prompt - Username [joe]:
            username = raw_input(_("Username") + " [%s]: " % getpass.getuser()).strip()
            if len(username) <= 0:
                username = getpass.getuser()

        if len(password) <= 0:
            # TRANSLATOR: This is a prompt - Password:
            password = getpass.getpass(_("Password") + ': ')

        # Create service proxy
        if url['scheme'][0:4] == "amqp":
            connection = '%s://%s:%s@%s:%s/%s' % (
                url['scheme'],
                username,
                password,
                url['host'],
                url['port'],
                url['path'])

            self.proxy = AMQPServiceProxy(connection, workers=4)

        # Default and HTTP
        elif url['scheme'][0:4] == "http":
            connection = '%s://%s:%s/%s' % (
                url['scheme'],
                url['host'],
                url['port'],
                url['path'])
            self.proxy = JSONServiceProxy(connection)

        else:
            print(_("The selected protocol is not supported!"))
            sys.exit(1)

        # Try to log in
        try:
            if not self.proxy.login(username, password):
                print(_("Login of user '%s' failed") % username)
                sys.exit(1)
        except Exception, e:
            print(e)
            sys.exit(1)

        return connection, username, password

    def reconnectJson(self, connection, username, password):
        self.proxy = JSONServiceProxy(connection)
        try:
            if self.proxy.login(username, password):
                pass
            else:
                sys.exit(1)
        except Exception, e:
            print(e)
            sys.exit(1)

    def help(self):
        """ Prints some help """
        mlist = {}
        for method, info in self.proxy.getMethods(None,
                ".".join(locale.getdefaultlocale())).iteritems():

            # Get the name of the module.
            module = info['target']
            if module not in mlist:
                mlist[module] = []

            sig = info['sig']
            args = ', '.join(sig)
            doc = ""
            if info['doc'] != None:
                d = ' '.join(info['doc'].split())
                for line in textwrap.wrap(d, 72):
                    doc += "    %s\n" % line
            mlist[module].append((method, args, doc))

        keylist = mlist.keys()
        keylist.sort()
        for module in keylist:
            print(module.upper())
            print("=" * len(module))
            mlist[module].sort()
            for mset in mlist[module]:
                print("  %s(%s)\n%s" % mset)


def main(argv=sys.argv):

    # Print help/usage and exit
    if '-h' in argv or '--help' in argv:
        print(__doc__)
        return 0
    try:
        opts, args = getopt.getopt(argv[1:], "u:p:c:", ["user=", "password=", "command="])
    except getopt.GetoptError:
        print(__doc__)
        sys.exit(2)

    service_uri = ''
    username = ''
    password = ''
    command = ''

    if len(args) >= 1:
        service_uri = args[0]

    for opt, arg in opts:
        if opt in ("-u", "--user"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-c", "--command"):
            command = arg

    # Create service object
    service = GOsaService()

    # Check if connection could be established
    try:
        service_uri, username, password = service.connect(service_uri, username, password)
    except KeyboardInterrupt:
        print()
        sys.exit(1)

    # Prepare to enter the interactive console.
    # Make the the GOsaService instance available to the console via the
    # "gosa" object.
    service.proxy.help = service.help
    context = {'gosa': service.proxy, '__name__': '__console__', '__doc__': None}

    # This python wrap string catches any exception, prints it and exists the
    # program with a failure that can be processed by the caller (e.g. on a
    # command line).
    wrap = """
import sys, traceback
try:
    %s
except:
    traceback.print_exc()
    sys.exit(1)
"""

    startup = """
import readline
import rlcompleter
import atexit
import os

# Tab completion
readline.parse_and_bind('tab: complete')

# history file
histfile = os.path.join(os.environ['HOME'], '.gosa.history')
try:
    readline.read_history_file(histfile)
except IOError:
    pass
atexit.register(readline.write_history_file, histfile)
del os, histfile, readline, rlcompleter
"""

    # Use script mode:
    if not sys.stdin.isatty():
        pyconsole = code.InteractiveInterpreter(context)
        try:
            cake = sys.stdin.read()
            pyconsole.runcode(cake)
            letRun = 0
        except Exception:
            traceback.print_exc()
            return 1
    # Use one-shot mode
    elif len(argv) >= 5:
        pyconsole = code.InteractiveInterpreter(context)
        try:
            commands = command.split(';')
            for cake in commands:
                pyconsole.runcode(wrap % cake)
            letRun = 0
        except Exception:
            return 1
    # Use interactive mode
    else:
        letRun = 1
        pyconsole = None
        while(letRun):
            try:
                if not pyconsole:
                    pyconsole = MyConsole(context)
                    pyconsole.runcode(startup)
                    pyconsole.interact(_("GOsa service shell. Use Ctrl+D to exit."))
                else:
                    mycode = pyconsole.getLastCode()
                    pyconsole = MyConsole(context)
                    pyconsole.runcode(mycode)
                    pyconsole.interact("")
                print(_("Closing session"))
                service.proxy.logout()
                letRun = 0
            # In case of a gosa-agent restart we have to double check login
            except HTTPError as e:
                if e.code == 401:
                    service.reconnectJson(service_uri, username, password)
                    context = {'gosa': service, 'service': service.proxy,
                        '__name__': '__console__', '__doc__': None}
                else:
                    print(e)
                    sys.exit(1)

    return 0

if __name__ == "__main__":
    sys.exit(main())
