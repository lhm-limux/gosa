#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import logging
import pkg_resources
import codecs
import traceback
import gobject
import dbus.mainloop.glib

from gosa.common import Environment
from gosa.dbus import __version__ as VERSION
from gosa.common.components.registry import PluginRegistry
from gosa.dbus import get_system_bus

loop = None

def shutdown(a=None, b=None):
    """ Function to shut down the client. """
    global loop

    env = Environment.getInstance()
    env.log.info("GOsa DBUS is shutting down")

    # Shutdown plugins
    PluginRegistry.shutdown()
    if loop:
        loop.quit()

    logging.shutdown()
    exit(0)


def handleSignal():
    """ Signal handler which will shut down the whole machinery """
    #TODO: Fine grained handling of signals
    shutdown()


def mainLoop(env):
    global loop

    try:
        # connect to dbus and setup loop
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        system_bus = get_system_bus()

        # Instanciate dbus objects
        pr = PluginRegistry(component='gosa_dbus.modules')

        # Enter main loop
        loop = gobject.MainLoop()
        loop.run()

    except Exception as detail:
        env.log.critical("unexpected error in mainLoop")
        env.log.exception(detail)
        env.log.debug(traceback.format_exc())

    finally:
        shutdown()


def main():
    """ Main programm which is called when the gosa agent process gets started.
        It does the main forking os related tasks. """

    # Inizialize core environment
    env = Environment.getInstance()
    env.log.info("GOsa DBUS is starting up")

    # Are we root?
    if os.geteuid() != 0:
        env.log.critical("GOsa DBUS must be run as root")
        exit(1)

    # Configured in daemon mode?
    if not env.config.get('dbus.foreground', default=env.config.get('core.foreground')):
        import signal
        import daemon
        import lockfile
        from lockfile import AlreadyLocked, LockFailed

        pidfile = None

        try:
            pidfile = env.config.get("dbus.pidfile",
                default="/var/run/gosa/gosa-dbus.pid")

            # Check if pid path if writable for us
            piddir = os.path.dirname(pidfile)
            os.stat(piddir)

            context = daemon.DaemonContext(
                working_directory=env.config.get("dbus.workdir",
                    default=env.config.get("core.workdir")),
                umask=int(env.config.get("dbus.umask", default="2")),
                pidfile=lockfile.FileLock(pidfile),
            )

            context.signal_map = {
                signal.SIGTERM: shutdown,
                signal.SIGHUP: shutdown,
            }

            context.uid = 0
            context.gid = 0

        except AlreadyLocked:
            env.log.critical("pid file '%s' is already in use" % pidfile)
            exit(1)

        except LockFailed:
            env.log.critical("cannot aquire lock '%s'" % pidfile)
            exit(1)

        else:

            try:
                with context:
                    # Write out pid to allow clean shutdown
                    pid = os.getpid()
                    env.log.debug("forked process with pid %s" % pid)

                    try:
                        pid_file = open(env.config.get('dbus.pidfile', default="/var/run/gosa/gosa-dbus.pid"), 'w')
                        try:
                            pid_file.write(str(pid))
                        finally:
                            pid_file.close()
                    except IOError:
                        env.log.error("cannot write pid file %s" %
                                env.config.get('dbus.pidfile', default="/var/run/gosa/gosa-dbus.pid"))
                        exit(1)

                    mainLoop(env)

            except daemon.daemon.DaemonOSEnvironmentError as detail:
                env.log.critical("error while daemonizing: " + str(detail))
                exit(1)

    else:
        mainLoop(env)


if __name__ == '__main__':
    if not sys.stdout.encoding:
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)
    if not sys.stderr.encoding:
        sys.stderr = codecs.getwriter('utf8')(sys.stderr)

    pkg_resources.require('gosa.common==%s' % VERSION)

    main()
