#!/usr/bin/env python
import re
import os

mod = re.compile(r"^(setup_[a-z0-9]+)\.py$")

for filename in os.listdir("."):
    candidate = mod.match(filename)
    if candidate:
        __import__(candidate.groups()[0])
