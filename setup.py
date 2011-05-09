#!/usr/bin/env python
import os
import sys

modules = ['gosa.common',
    'gosa.agent',
    'gosa.dbus',
    'gosa.client',
    'gosa.shell']

for module in modules:
    os.system("cd %s && ./setup.py %s" % (module, " ".join(sys.argv[1:])))

for root, dirs, files in os.walk("plugins"):
    if "setup.py" in files:
        os.system("cd %s && ./setup.py %s" % (root, " ".join(sys.argv[1:])))




#import re
#import os
#
#mod = re.compile(r"^(setup_[a-z0-9]+)\.py$")
#
#for filename in os.listdir("."):
#    candidate = mod.match(filename)
#    if candidate:
#        __import__(candidate.groups()[0])
