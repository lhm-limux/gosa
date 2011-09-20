#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common import Environment
from gosa.common.components import AMQPServiceProxy

from time import time

import errno
import os
import re
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
macaddress = re.compile("^[0-9a-f]{1,2}-[0-9a-f]{1,2}-[0-9a-f]{1,2}-[0-9a-f]{1,2}-[0-9a-f]{1,2}-[0-9a-f]{1,2}$")
static = os.getcwd() + '/pxelinux.static'

# Create connection to service
proxy = AMQPServiceProxy('amqps://cajus:tester@amqp.intranet.gonicus.de/org.gosa')


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
        Environment.config="fts.conf"
        Environment.noargs=True
        env = Environment.getInstance()
        self.positive_cache_timeout = 10

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
        elif macaddress.match(path[4:]):
            result = self.getBootParams(path)[offset:offset+size]
        elif path.lstrip(os.sep) in self.filesystem[self.root].keys():
            result = str(self.filesystem[self.root][path.lstrip(os.sep)]['content'])[offset:offset+size]
        return result

    def getSize(self, path):
        result = 0
        if os.path.exists(os.sep.join((static, path))):
            result = os.path.getsize(os.sep.join((static, path)))
        elif macaddress.match(path[4:]):
            result = len(self.getBootParams(path))
        elif path.lstrip(os.sep) in self.filesystem[self.root].keys():
            result = len(str(self.filesystem[self.root][path.lstrip(os.sep)]['content']))
        return result

    def getBootParams(self, path):
        # Need to transform /01-00-00-00-00-00-00 into 00:00:00:00:00:00
        if not path in self.filesystem[self.root].keys() or self.filesystem[self.root][path]['timestamp'] < int(time()) - int(self.positive_cache_timeout):
            self.filesystem[self.root][path] = {}
            self.filesystem[self.root][path]['content'] = str(proxy.systemGetBootString(None, path[4:].replace('-', ':')))
            self.filesystem[self.root][path]['timestamp'] = time()
        return self.filesystem[self.root][path]['content']


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
    server.parser.add_option(mountopt="root", metavar="PATH", default=os.sep, help="mirror filesystem from under PATH [default: %default]")
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
