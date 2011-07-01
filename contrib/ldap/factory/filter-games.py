# -*- coding: utf-8 -*-

class ObjectBackend(object):
    pass


class LDAPBackend(ObjectBackend):

    def __init__(self):
        #TODO: load schema
        pass

    def loadAttr(self, uuid, key):
        #TODO: load entry (non-cached)
        return ["s3cr3t"]


class ObjectBackendRegistry(object):

    instance = None
    backends = {}
    uuidAttr = "entryUUID"

    def __init__(self):
        # Load available backends
        #TODO: this is hard coded LDAP stuff in the moment,
        #      load from configuration later on
        ObjectBackendRegistry.backends['ldap'] = LDAPBackend()

    def dn2uuid(self, dn):
        #TODO: missing dn mapping
        return "d47afd0c-0f1c-102b-93c4-d7eaa5111f95"

    @staticmethod
    def getInstance():
        if not ObjectBackendRegistry.instance:
            ObjectBackendRegistry.instance = ObjectBackendRegistry()

        return ObjectBackendRegistry.instance

    @staticmethod
    def getBackend(name):
        if not name in ObjectBackendRegistry.backends:
            raise ValueError("no such backend '%s'" % name)

        return ObjectBackendRegistry.backends[name]


###
### OUT
###

def copyAttr(obj, dst, src, target):
    return {target: getattr(obj, src)}

def mkunixpasswd(obj, dst):
    return {"userPassword": "{%s}%s" % (obj.PasswordMethod, obj.Password)}

def mksmbpasswd(obj, dst):
    return {"sambaLMPasswd": "asdfasdfasdfasdf:asdfasdfasdfasdf",
            "sambaNTPasswd": "asdfdfghdfghdfgh:xcvbxcvbxcvbxcvb"}

def loadAttr(obj, key):
    backend = ObjectBackendRegistry.getBackend(obj._backend)
    return backend.loadAttr(obj.uuid, key)

#---------------------------------------

fltr1 = """
dst.update(copyAttr(obj, dst, key, 'userPassword'))
"""

fltr2 = """
dst.update(mkunixpasswd(obj, dst))
dst.update(mksmbpasswd(obj, dst))
"""

fltr3 = """
dst = loadAttr(obj, "userPassword")[0].upper()
"""
#---------------------------------------



class klass(object):
    _backend = "ldap"
    PasswordMethod = "MD5"
    Password = "secret"

    def load(self, dn):
        self.reg = ObjectBackendRegistry.getInstance()
        self.uuid = self.reg.dn2uuid(dn)

obj = klass()
key = "Password"
dst = {}
#exec fltr2
#print dst


###
### IN
###

obj.load("cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")
exec fltr3
print dst
