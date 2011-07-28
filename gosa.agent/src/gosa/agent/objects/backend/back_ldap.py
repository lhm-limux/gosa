# -*- coding: utf-8 -*-
import ldap
import ldap.schema
from backend import ObjectBackend


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

    def loadAttrs(self, uuid, keys):
        res = self.con.search_s(self.base, ldap.SCOPE_SUBTREE, 'entryUUID=%s' % uuid,
                keys)[0][1]
        return dict((k,v) for k, v in res.iteritems() if k in keys)

    def dn2uuid(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_BASE, 'objectClass=*',
                ['entryUUID'])[0][1]['entryUUID'][0]
        return res