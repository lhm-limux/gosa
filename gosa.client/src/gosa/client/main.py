#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: main.py 1050 2010-10-08 06:55:44Z cajus $$

 See LICENSE for more information about the licensing.
"""
import os
import time
import sys
import logging
import pkg_resources
import codecs
import traceback

from gosa.common.env import Environment
from gosa.client import __version__ as VERSION
from gosa.common.components.registry import PluginRegistry
from gosa.common.event import EventMaker


def shutdown(a=None, b=None):
    env = Environment.getInstance()

    """ Function to shut down the client. Do some clean up and close sockets."""
    amqp = PluginRegistry.getInstance("AMQPClientHandler")
    amqp_service = PluginRegistry.getInstance("AMQPClientService")

    # Tell others that we're away now
    e = EventMaker()
    goodbye = e.Event(e.ClientLeave(e.Id(env.uuid)))
    amqp.sendEvent(goodbye)

    # Shutdown plugins
    PluginRegistry.shutdown()

    logging.shutdown()
    exit(0)


def handleSignal():
    """ Signal handler which will shut down the whole machinery """
    #TODO: Fine grained handling of signals
    shutdown()


def mainLoop(env):
    """ Main event loop which will process all registerd threads in a loop.
        It will run as long env.active is set to True."""
    try:
        # Load plugins
        pr = PluginRegistry(component='gosa_client.modules')
        amqp = PluginRegistry.getInstance("AMQPClientHandler")

        #TODO:
        # Check if we're a client
        # -> no: shutdown, client should be joined by administrator before
        #        calling the client

        # Sleep and slice
        wait = 2
        while True:
            # Threading doesn't seem to work well with python...
            for p in env.threads:

                # Bail out if we're active in the meanwhile
                if not env.active:
                    break

                p.join(wait)

            # No break, go to main loop
            else:
                continue

            # Break, leave main loop
            break

    except Exception as detail:
        env.log.critical("unexpected error in mainLoop")
        env.log.exception(detail)
        env.log.debug(traceback.format_exc())

    finally:
        for p in env.threads:
            if hasattr(p, 'stop'):
                p.stop()

        shutdown()


def main():
    """ Main programm which is called when the gosa agent process gets started.
        It does the main forking os related tasks. """

    # Inizialize core environment
    env = Environment.getInstance()
    env.log.info("GOsa client is starting up")

    # Configured in daemon mode?
    if not env.config.getOption('foreground', section="client", default=env.config.getOption('foreground')):
        import grp
        import pwd
        import stat
        import signal
        import daemon
        import lockfile
        from lockfile import AlreadyLocked, LockFailed

        pidfile = None

        # Running as root?
        if os.geteuid() != 0:
            env.log.critical("GOsa client needs to be started as root in non foreground mode")
            exit(1)

        try:
            user = env.config.getOption("user", section="client")
            group = env.config.getOption("group", section="client")
            pidfile = env.config.getOption("pidfile", section="client",
                    default="/var/run/gosa/gosa-client.pid")

            # Check if pid path if writable for us
            piddir = os.path.dirname(pidfile)
            pwe = pwd.getpwnam(user)
            gre = grp.getgrnam(group)
            try:
                s = os.stat(piddir)
            except Exception as e:
                env.log.critical("cannot stat pid directory '%s' - %s" % (piddir, str(e)))
                exit(1)
            mode = s[stat.ST_MODE]

            if not bool(((s[stat.ST_UID] == pwe.pw_uid) and (mode & stat.S_IWUSR)) or \
                   ((s[stat.ST_GID] == gre.gr_gid) and (mode & stat.S_IWGRP)) or \
                   (mode & stat.S_IWOTH)):
                   env.log.critical("cannot aquire lock '%s' - no write permission for group '%s'" % (piddir, group))
                   exit(1)

            # Has to run as root?
            if pwe.pw_uid == 0:
                env.log.warning("GOsa client should not be configured to run as root")

            context = daemon.DaemonContext(
                working_directory=env.config.getOption("workdir",
                    section="client",
                    default=env.config.getOption("workdir")),
                umask=int(env.config.getOption("umask", section="client", default="2")),
                pidfile=lockfile.FileLock(pidfile),
            )

            context.signal_map = {
                signal.SIGTERM: shutdown,
                signal.SIGHUP: shutdown,
            }

            context.uid = pwd.getpwnam(user).pw_uid
            context.gid = grp.getgrnam(group).gr_gid

        except KeyError:
            env.log.critical("cannot resolve user:group '%s:%s'" %
                (user, group))
            exit(1)

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
                        pid_file = open(env.config.getOption('pidfile', section="client", default="/var/run/gosa/gosa-client.pid"), 'w')
                        try:
                            pid_file.write(str(pid))
                        finally:
                            pid_file.close()
                    except IOError:
                        env.log.error("cannot write pid file %s" %
                                env.config.getOption('pidfile', section="client", default="/var/run/gosa/gosa-client.pid"))
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