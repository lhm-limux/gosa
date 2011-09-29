# -*- coding: utf-8 -*-
from gosa.agent.objects import GOsaObjectFactory
import time
import datetime

f = GOsaObjectFactory('.')
p = f.getObject('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
#print "Object type:", type(p)
#print "sn:", p.sn
#print "commonName:", p.commonName
print "givenName:", p.givenName
print "userPassword:", p.userPassword
print "passwordMethod:", p.passwordMethod
print "dateOfBirth:", p.dateOfBirth
print "gotoLastSystemLogin:", p.gotoLastSystemLogin
#p.sn = u"Name"
#p.givenName = u"Neuer"
#p.notify(u"This is my title", u"To my amazing message!")
#p.notify(notify_title = u"This is my title", notify_message = u"To my amazing message!")
#p.notify(notify_message = u"To my amazing message!")

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
p.uid = u"hickert"
p.givenName = u"Fabian"
p.sn = u"Hickert"
p.userPassword = u"tollessecret"
p.roomNumber = 22
p.jpegPhoto =  open('dummy.binary', 'r').read()
p.gotoLastSystemLogin = datetime.datetime.today()
p.dateOfBirth = datetime.datetime.today().date()
p.gender = "M"
p.commit()
