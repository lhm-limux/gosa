#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import sys
import os
from gosa.agent.objects import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObject('SambaUser', u"cn=Playground Tester,ou=people,dc=gonicus,dc=de")

print p.sambaLogonScript
for prop in p.propertyNames:
    print "Attribute %s: %s" % (prop.ljust(40), getattr(p, prop))

p.commit()
