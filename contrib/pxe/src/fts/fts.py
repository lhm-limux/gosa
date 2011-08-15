#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010, 2011 GONICUS GmbH

 ID: $$Id: fts.py 487 2011-08-10 07:34:06Z cajus $$

 See LICENSE for more information about the licensing.
"""

from gosa.common import Environment
from gosa.common.components import AMQPServiceProxy

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

testclients = {
    "de:ad:d9:57:56:d5": "install"
}

static=os.getcwd()+'/pxelinux.static'

# Create connection to service
#try:
#    proxy = AMQPServiceProxy('amqps://ldapadmin:secret@amqp.intranet.gonicus.de/org.gosa')
#    print proxy.systemGetBootParams(None, 'de:ad:d9:57:56:d5')
#except:
#    raise

def getDepth(path):
    """
    Return the depth of a given path, zero-based from root ('/')
    """
    if path=='/':
        return 0
    else:
        return path.count('/')

def getParts(path):
    """
    Return the slash-separated parts of a given path as a list
    """
    if path=='/':
        return [['/']]
    else:
        return path.split('/')

class FileStat(fuse.Stat):
    def __init__(self):
        self.st_mode = stat.S_IFDIR | 0755
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 2
        self.st_uid = os.getuid()
        self.st_gid = os.getgid()
        self.st_size = 4096
        self.st_atime = int(time())
        self.st_mtime = self.st_atime
        self.st_ctime = self.st_atime

class PxeFS(Fuse):
    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        self.root = os.sep
        self.filesystem = {
            self.root : {
                "content": "",
            }
        }

        for testclient in testclients.keys():
            self.filesystem[self.root]= { testclient : { "content" : r'''vga=normal initrd=debian-installer/i386/initrd.gz
netcfg/choose_interface=eth0 locale=de_DE debian-installer/country=DE
debian-installer/language=de
debian-installer/keymap=de-latin1-nodeadkeys
console-keymaps-at/keymap=de-latin1-nodeadkeys auto-install/enable=false
preseed/url=https://amqp.intranet.gonicus.de:8080/preseed/de-ad-d9-57-56-d5 debian/priority=critical hostname=dyn-10 domain=please-fixme.org DEBCONF_DEBUG=5 svc_key=f1p8zRBGrUA26Nn+2qBS/JC8KOXHTEfgIEq5Le2WC4jW2xUuVzzHnO9LYiH8hYLNXHo7V9+2Aiz8\n/XU6xxcusWUiMjXgdZcDe8wJtXR5krg=\n''' } }

    def getattr(self, path):
        result = FileStat()
        if path == self.root:
            pass
        elif os.path.exists(os.sep.join((static, path))):
            result = os.stat(os.sep.join((static, path)))
        else:
            result.st_mode = stat.S_IFREG | 0666
            result.st_nlink = 1
            result.st_size = self.getSize(path)
        return result

    def read(self, path, size, offset):
        return self.getContent(path, size, offset)

    def flush(self, filehandle=None):
        return 0

    def readdir(self, path, offset):
        direntries=[ '.', '..' ]
        if os.path.exists(os.sep.join((static, path))):
            direntries.extend(os.listdir(os.sep.join((static, path))))
        elif self.filesystem[path].keys():
            direntries.extend(self.filesystem[path].keys())
        for directory in direntries:
            yield fuse.Direntry(directory)

    def getContent(self, path, size, offset):
        result = ""
        if os.path.exists(os.sep.join((static, path))):
            with open(os.sep.join((static, path))) as f:
                f.seek(offset)
                result = f.read(size)
        elif path.lstrip(os.sep) in self.filesystem[self.root].keys():
            result = str(self.filesystem[self.root][path.lstrip(os.sep)]["content"])[offset:offset+size]
        return result

    def getSize(self, path):
        result = 0
        if os.path.exists(os.sep.join((static, path))):
            result = os.path.getsize(os.sep.join((static, path)))
        elif path.lstrip(os.sep) in self.filesystem[self.root].keys():
            result = len(str(self.filesystem[self.root][path.lstrip(os.sep)]["content"]))
        return result


def main():
    usage = """
Userspace tftp supplicant: create pxelinux configuration files based on external state information.

""" + Fuse.fusage

    server = PxeFS(version="%prog " + fuse.__version__,
                 usage=usage,
                 dash_s_do='setsingle')

    # Disable multithreading: if you want to use it, protect all method of
    # XmlFile class with locks, in order to prevent race conditions
    server.multithreaded = False
    server.parser.add_option(mountopt="root", metavar="PATH", default='/', help="mirror filesystem from under PATH [default: %default]")
    server.parse(values=server, errex=1)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.root)
    except OSError:
        print >> sys.stderr, "can't enter root of underlying filesystem"
        sys.exit(1)

    server.main()

if __name__ == '__main__':
    main()
