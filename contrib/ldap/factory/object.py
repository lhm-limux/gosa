# -*- coding: utf-8 -*-
from factory import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person')
print "Object type:", type(p)

p.sn = u"Pollmeier"
print "sn:", p.sn
p.commit()
#p.notify("Achtung!", "Hallo Karl-Gustav ;-)")
