# -*- coding: utf-8 -*-
from gosa.agent.objects import GOsaObjectFactory

f = GOsaObjectFactory('.')
p = f.getObjectInstance('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")


#print "Object type:", type(p)
#print "sn:", p.sn
#print "cn:", p.cn


#p.sn = u"Nameneu"
#p.userPassword = u"secret"
#p.givenName = u"Neuer"
#p.notify(u"This is my title", u"To my amazing message!")
#p.notify(notify_title = u"This is my title", notify_message = u"To my amazing message!")
#p.notify(notify_message = u"To my amazing message!")

#print "givenName:", p.givenName
#print "cn:", p.cn
#print "sn:", p.sn
#p.commit()

#print "Object type:", type(p)
#print "sn:", p.sn
#print "cn:", p.cn

#p.sn = u"Hickert"
p.userPassword = u"tollessecret"
p.givenName = u"Fabian"
p.sn = u"Hickert"
p.cn = u"Test"

p.commit()
