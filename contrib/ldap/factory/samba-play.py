#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import sys
import os
import pprint
from gosa.agent.objects import GOsaObjectFactory

f = GOsaObjectFactory()
p = f.getObject('SambaUser', u"cn=Playground Tester,ou=people,dc=gonicus,dc=de", mode="update")

for prop in p.listProperties():
    print "Attribute %s: %s" % (prop.ljust(40), getattr(p, prop))

#p.sambaLogonTime = datetime.datetime.today()
#p.sambaPwdCanChange = datetime.datetime.today()
#p.sambaKickoffTime = datetime.datetime.today()
#p.sambaLogoffTime = datetime.datetime.today()
#p.sambaPwdLastSet = datetime.datetime.today()
#p.sambaBadPasswordTime = datetime.datetime.today()
#p.sambaPwdMustChange = datetime.datetime.today()
#p.sambaBadPasswordCount = 5
#p.displayName = "PeterPan"

#p.passwordNotRequired = True
p.serverTrustAccount = not p.serverTrustAccount
p.sambaHomePath = r"\\hallo\welt"
p.sambaHomeDrive = "D:"

for entry in p.sambaLogonHours:
    print("%s: %s" % (entry, p.sambaLogonHours[entry]))

#p.commit()
#print p._extends
