# -*- coding: utf-8 -*-
from factory import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
print "Object type:", type(p)
print "sn:", p.sn
p.sn = u"Dengler"
p.commit()
#p.notify("Achtung!", "Hallo Karl-Gustav ;-)")
