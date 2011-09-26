#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common import Environment

import os
import subprocess
import sys

def main():
    usage = """
Userspace tftp supplicant: create pxelinux configuration files based on external state information.

"""

    Environment.config="fts.conf"
    Environment.noargs=True
    env = Environment.getInstance()
    cfg_path = env.config.get('pxelinux_cfg-path', default = os.sep.join((os.getcwd(), 'pxelinux.cfg')))
    static_path = env.config.get('pxelinux_static-path', default = os.sep.join((os.getcwd(), 'pxelinux.static')))
    if not os.access(cfg_path, os.F_OK):
        self.env.log.error("The pxelinux_cfg-path {path} does not exist!".format(path=cfg_path))
    if not os.access(static_path, os.F_OK):
        self.env.log.error("The pxelinux_static-path {path} does not exist!".format(path=static_path))

    # TODO: Use reliable method to start and control daemon process
    debug = "-d"
    p = subprocess.Popen(
        "{path}/fts-fuse.py -f {debug} {cfg_path}".format(path=os.getcwd(), debug=debug, cfg_path=cfg_path),
        shell=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    result = os.waitpid(p.pid, 0)
    sys.exit(result)

if __name__ == '__main__':
    main()
