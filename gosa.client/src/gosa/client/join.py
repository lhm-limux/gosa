#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: amqp_service.py 1006 2010-09-30 12:43:58Z cajus $$

 This modules hosts AMQP service related classes.

 See LICENSE for more information about the licensing.
"""
import signal
import sys
import time
import re
import os
import gettext
import grp
import pkg_resources
from os.path import isdir, exists
from pkg_resources import resource_filename
from gosa.common.env import Environment
from gosa.common.config import ConfigNoFile
from operator import itemgetter

# Include locales
t = gettext.translation('messages', resource_filename("gosa.client", "locale"), fallback=True)
_ = t.ugettext
joiner = None


def signal_handler(signal, frame):
    joiner.end_gui()
    sys.exit(0)


def main():
    global joiner

    # Init handler
    signal.signal(signal.SIGINT, signal_handler)

    # Load modules
    modules = {}
    priority = {}
    for entry in pkg_resources.iter_entry_points("gosa_join.modules"):
        mod = entry.load()
        if mod.available():
            priority[mod.__name__] = mod.priority
            modules[mod.__name__] = mod

    # Take the one with the highest priority
    #module = "CursesGUI" # Force module for testing
    module = sorted(priority.items(), key=itemgetter(1))[0][0]

    # Try to load environment. If it doesn't work, evaluate
    # config file from command line and create a default one.
    try:
        env = Environment.getInstance()
    except ConfigNoFile:
        config_file = "/etc/gosa/config"

        # Try to find config file without optparser
        for (i, arg) in enumerate(sys.argv):
            r = re.match(r"--config=(.*)", arg)
            if r:
                config_file = r.groups(0)[0]
                break

            if arg == "--config" or arg == "-c":
                config_file = sys.argv[i+1]
                break

        # Check if config path exists
        config_dir = os.path.dirname(config_file)
        if not exists(config_dir):
            os.mkdir(config_dir)

        if not isdir(config_dir):
            print("Error: configuration directory %s is no directory!" % config_dir)
            exit(1)

        # Read default config and write it back to config_file
        config = open(resource_filename("gosa.client", "data/client.conf")).read()
        with open(config_file, "w") as f:
            f.write(config)

        # Nothing important here yet, but lock us down
        os.chmod(config_file, 0600)
        env = Environment.getInstance()


    # Instanciate joiner and ask for help
    joiner = modules[module]()
    if not joiner.test_login():
        joiner.join_dialog()

    # Fix configuration file permission
    cfg = env.config.getOption("config")
    group = env.config.getOption("group", "client", default="gosa-ng")
    try:
        gid = grp.getgrnam(group).gr_gid
    except KeyError as e:
        print("Error: failed to resolve user/group - %s" % str(e))
        exit(1)

    # Fix configuration file permission
    env.log.debug("setting ownership for '%s' to (%s/%s)" % (cfg, "root", group))
    os.chown(cfg, 0, gid)
    env.log.debug("setting permission for '%s' to (%s)" % (cfg, '0640'))
    os.chmod(cfg, 0640)


if __name__ == '__main__':
    # check for root permission
    if os.geteuid() != 0:
        print("Error: you need to be root to join to a gosa-ng network!")
        exit()

    main()
