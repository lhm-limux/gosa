# -*- coding: utf-8 -*-
import ldap
import ldap.schema
from backend import ObjectBackend
from gosa.agent.ldap_utils import LDAPHandler


class LDAP(ObjectBackend):

    def __init__(self):
        # Load LDAP handler class
        self.lh = LDAPHandler.get_instance()
        self.con = self.lh.get_connection()

    def __del__(self):
        self.lh.free_connection(self.con)

    def loadAttrs(self, uuid, keys):
        res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE, 'entryUUID=%s' % uuid,
                keys)[0][1]
        return dict((k,v) for k, v in res.iteritems() if k in keys)

    def dn2uuid(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_BASE, 'objectClass=*',
                ['entryUUID'])[0][1]['entryUUID'][0]
        return res
