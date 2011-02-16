#!/usr/bin/env python
#-*- coding: utf-8 -*-
import os
import sys
from subprocess import call

builds = [ 
    "src/gosa/common",
    "src/gosa/agent",
    "src/gosa/client",
    "src/gosa/agent",
    "src/plugins/libinst",
    ]

here = os.path.abspath(os.path.dirname(__file__))

for build in builds:
    os.chdir(here + "/" + build)
    if call(sys.argv):
        exit(1)

os.chdir(here)
