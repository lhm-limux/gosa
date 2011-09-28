# -*- coding: utf-8 -*-
from gosa.agent.objects import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObject('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
print "Object type:", type(p)
print "sn:", p.sn
print "commonName:", p.commonName
p.sn = u"Name"
p.givenName = u"Neuer"
p.notify(u"This is my title", u"To my amazing message!")
p.notify(notify_title = u"This is my title", notify_message = u"To my amazing message!")
p.notify(notify_message = u"To my amazing message!")


print "sn:", p.sn
p.commit()
