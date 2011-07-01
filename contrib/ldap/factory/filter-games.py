# -*- coding: utf-8 -*-
from backend.registry import loadAttr, ObjectBackendRegistry

###
### OUT Test
###

def copyAttr(obj, dst, src, target):
    return {target: getattr(obj, src)}

def mkunixpasswd(obj, dst):
    return {"userPassword": "{%s}%s" % (obj.PasswordMethod, obj.Password)}

def mksmbpasswd(obj, dst):
    return {"sambaLMPasswd": "asdfasdfasdfasdf:asdfasdfasdfasdf",
            "sambaNTPasswd": "asdfdfghdfghdfgh:xcvbxcvbxcvbxcvb"}

#---------------------------------------

fltr1 = """
dst.update(copyAttr(obj, dst, key, 'userPassword'))
"""

fltr2 = """
dst.update(mkunixpasswd(obj, dst))
dst.update(mksmbpasswd(obj, dst))
"""

fltr3 = """
dst = loadAttr(obj, "givenName")[0]
"""
#---------------------------------------



class klass(object):
    _backend = "ldap"
    PasswordMethod = "MD5"
    Password = "secret"

    def load(self, dn):
        self.reg = ObjectBackendRegistry.getInstance()
        self.uuid = self.reg.dn2uuid(self._backend, dn)

obj = klass()
key = "GivenName"
dst = {}
#exec fltr2
#print dst


###
### IN
###

obj.load("cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
exec fltr3
print dst
