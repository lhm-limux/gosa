#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010, 2011 GONICUS GmbH

 ID: $$Id: fts.py 487 2011-08-10 07:34:06Z cajus $$

 See LICENSE for more information about the licensing.
"""

from time import time

import errno
import os
import stat

try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse

fuse.fuse_python_api = (0, 2)

if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.feature_assert('stateful_files', 'has_init')

class FTS(Fuse):
    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        self.root="/"

def main():
    usage = """
Userspace nullfs-alike: mirror the filesystem tree from some point on.

""" + Fuse.fusage

    server = FTS(version="%prog " + fuse.__version__,
                 usage=usage,
                 dash_s_do='setsingle')

    # Disable multithreading: if you want to use it, protect all method of
    # XmlFile class with locks, in order to prevent race conditions
    server.multithreaded = False

    server.parser.add_option(mountopt="root", metavar="PATH", default='/',
                             help="mirror filesystem from under PATH [default: %default]")
    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.root)
    except OSError:
        print >> sys.stderr, "can't enter root of underlying filesystem"
        sys.exit(1)

    server.main()

if __name__ == '__main__':
    #fs = FTS()
    #fs.parse(errex=1)
    #fs.flags = 0
    #fs.multithreaded = 0
    #fs.main()
    main()
