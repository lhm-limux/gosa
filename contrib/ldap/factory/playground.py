# -*- coding: utf-8 -*-
from gosa.agent.objects.factory import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
print "Object type:", type(p)
print "sn:", p.sn
print "cn:", p.cn
p.sn = u"Dengler lengler"
print "sn:", p.sn
p.commit()
#p.notify("Achtung!", "Hallo Karl-Gustav ;-)")
