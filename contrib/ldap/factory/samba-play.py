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

p.commit()
