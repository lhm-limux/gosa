#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import logging
import pkg_resources
import codecs

from gosa.common import Environment
from gosa.common.utils import SystemLoad
from gosa.common.event import EventMaker
from gosa.common.components import ObjectRegistry, PluginRegistry
from gosa.agent import __version__ as VERSION


def shutdown(a=None, b=None):
    """ Function to shut down the agent. Do some clean up and close sockets."""
    amqp = PluginRegistry.getInstance("AMQPHandler")

    # Tell others that we're away now
    e = EventMaker()
    goodbye = e.Event(e.NodeLeave(e.Id(amqp.env.id)))
    amqp.sendEvent(goodbye)

    # Shutdown plugins
    PluginRegistry.shutdown()

    logging.shutdown()
    exit(0)


def handleSignal():
    """ Signal handler which will shut down the whole machinery """
    #TODO: Fine grained handling of signals
    Environment.getInstance().active = False


def mainLoop(env):
    """ Main event loop which will process all registerd threads in a loop.
        It will run as long env.active is set to True."""
    try:
        # Load plugins
        pr = PluginRegistry()
        cr = PluginRegistry.getInstance("CommandRegistry")
        oreg = ObjectRegistry.getInstance()
        amqp = PluginRegistry.getInstance("AMQPHandler")

        wait = 2
        notifyInterval = 10
        interval = notifyInterval
        loadAvg = SystemLoad()

        # Sleep and slice
        while True:

            # Threading doesn't seem to work well with python...
            for p in env.threads:

                # Bail out if we're active in the meanwhile
                if not env.active:
                    break

                # Check if we reached the notification interval
                interval += wait
                if interval > notifyInterval:
                    interval = 0
                    load = loadAvg.getLoad()
                    latency = 0
                    workers = len(env.threads)
                    env.log.debug("load %s, latency %s, workers %s" %
                            (load, latency, workers))

                    e = EventMaker()
                    status = e.Event(
                        e.NodeStatus(
                            e.Id(env.id),
                            e.Load(str(load)),
                            e.Latency(str(latency)),
                            e.Workers(str(workers)),
                        )
                    )
                    amqp.sendEvent(status)

                # Disable potentially dead nodes
                cr.updateNodes()

                p.join(wait)

            # No break, go to main loop
            else:
                continue

            # Break, leave main loop
            break

    except Exception as detail:
        env.log.critical("unexpected error in mainLoop")
        env.log.exception(detail)

    finally:
        shutdown()


def main():
    """ Main programm which is called when the gosa agent process gets started.
        It does the main forking os related tasks. """

    # Inizialize core environment
    env = Environment.getInstance()
    env.log.info("GOsa is starting up")

    # Configured in daemon mode?
    if not env.config.get('core.foreground'):
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
            env.log.critical("GOsa agent needs to be started as root in non foreground mode")
            exit(1)

        try:
            user = env.config.get("core.user")
            group = env.config.get("core.group")

            pidfile = env.config.get("core.pidfile", default="/var/run/gosa/gosa-agent.pid")

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
                env.log.warning("GOsa agent should not be configured to run as root")

            context = daemon.DaemonContext(
                working_directory=env.config.get("core.workdir"),
                umask=int(env.config.get("core.umask")),
                pidfile=lockfile.FileLock(pidfile),
            )

            context.signal_map = {
                signal.SIGTERM: handleSignal,
                signal.SIGHUP: handleSignal,
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
                        pid_file = open(env.config.get('core.pidfile'), 'w')
                        try:
                            pid_file.write(str(pid))
                        finally:
                            pid_file.close()
                    except IOError:
                        env.log.error("cannot write pid file %s" %
                                env.config.get('core.pidfile'))
                        exit(1)

                    mainLoop(env)

            except daemon.daemon.DaemonOSEnvironmentError as detail:
                env.log.critical("error while daemonizing: " + str(detail))
                exit(1)

    else:
        if env.config.get('core.profile'):
            import cProfile
            import gosa.common.lsprofcalltree
            p = cProfile.Profile()
            p.runctx('mainLoop(env)', globals(), {'env': env})
            k = gosa.common.lsprofcalltree.KCacheGrind(p)
            data = open('prof.kgrind', 'w+')
            k.output(data)
            data.close()
        else:
            mainLoop(env)


if __name__ == '__main__':
    if not sys.stdout.encoding:
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)
    if not sys.stderr.encoding:
        sys.stderr = codecs.getwriter('utf8')(sys.stderr)

    pkg_resources.require('gosa.common==%s' % VERSION)
    main()
