# -*- coding: utf-8 -*-
from gosa.agent.objects import GOsaObjectFactory
import time
import datetime
import sys

f = GOsaObjectFactory('.')
p = f.getObject('Person', u'dc=gonicus,dc=de', create=True)
#p = f.getObject('Person', u"cn=Fabian Sebastian2 Hickert (Ja es geht!),ou=people,ou=ehemalige,ou=Virtuelle Mailbenutzer,ou=gonicus.de,ou=Mail-Domänen,dc=gonicus,dc=de")
#print "Object type:", type(p)
#print "sn:", p.sn
#print "commonName:", p.commonName
#print "givenName:", p.givenName
#print "userPassword:", p.userPassword
#print "passwordMethod:", p.passwordMethod
#print "dateOfBirth:", p.dateOfBirth
#print "gotoLastSystemLogin:", p.gotoLastSystemLogin
#print "roomNumber:", p.roomNumber
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
#p.roomNumber += 1
#open('dummy.gif_read', 'w').write(p.jpegPhoto)
p.jpegPhoto =  open('dummy.gif', 'r').read()
p.gotoLastSystemLogin = datetime.datetime.today()
p.dateOfBirth = datetime.datetime.today().date()
p.gender = "M"
p.telephoneNumber = ['123', '333' ]
p.commit()
