# -*- coding: utf-8 -*-
import ldap
import ldap.schema


class ObjectBackend(object):

    def loadAttr(self, uuid, key, target_type):
        raise NotImplementedError("object backend is missing loadAttr()")

    def dn2uuid(self, dn):
        raise NotImplementedError("object backend is not capable of mapping DN to UUID")


class LDAPBackend(ObjectBackend):

    def __init__(self):
        #TODO: config
        self.url = "ldap://vm-ldap.intranet.gonicus.de"
        self.base = "dc=gonicus,dc=de"

        # Load schema
        con = ldap.initialize(self.url)
        con.protocol = ldap.VERSION3
        con.simple_bind_s()
        #res = con.search_s('cn=subschema', ldap.SCOPE_BASE, 'objectClass=*',
        #        ['*', '+'])[0][1]

        self.con = con
        #self.subschema = ldap.schema.SubSchema(res)

    def loadAttr(self, uuid, key, target_type):
        #TODO: type mapping, convert with help of schema
        res = self.con.search_s(self.base, ldap.SCOPE_SUBTREE, 'entryUUID=%s' % uuid,
                [key])[0][1][key]
        return res

    def dn2uuid(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_BASE, 'objectClass=*',
                ['entryUUID'])[0][1]['entryUUID'][0]
        return res


class ObjectBackendRegistry(object):
    instance = None
    backends = {}
    uuidAttr = "entryUUID"

    def __init__(self):
        # Load available backends
        #TODO: this is hard coded LDAP stuff in the moment,
        #      load from configuration later on
        ObjectBackendRegistry.backends['ldap'] = LDAPBackend()

    def dn2uuid(self, backend, dn):
        return ObjectBackendRegistry.backends['ldap'].dn2uuid(dn)

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
    #TODO: use attribute backend, not object backend
    #TODO: provide object type
    return backend.loadAttr(obj.uuid, key, None)

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
