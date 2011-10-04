#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import sys
import os
from gosa.agent.objects import GOsaObjectFactory

# use create, update, remove
if len(sys.argv) != 2:
    print "Usage: %s create|update|remove\n" % sys.argv[0]
    exit(0)

mode = sys.argv[1]
del sys.argv[1]

f = GOsaObjectFactory('.')

if mode == "create":
    p = f.getObject('Person', u'ou=people,dc=gonicus,dc=de', create=True)

if mode == "update" or mode == "remove":
    p = f.getObject('Person', u"cn=Fabian Hickert (Ja es geht!),ou=people,dc=gonicus,dc=de")

if mode == "remove":
    p.remove()
    exit(0)

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
