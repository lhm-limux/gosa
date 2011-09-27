# -*- coding: utf-8 -*-
import ldap
import ldap.filter
import ldap.schema
from logging import getLogger
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler
from gosa.agent.objects.backend.backend import ObjectBackend, EntryNotFound, EntryNotUnique


class LDAP(ObjectBackend):

    def __init__(self):
        # Load LDAP handler class
        self.env = Environment.getInstance()
        self.log = getLogger(__name__)

        self.lh = LDAPHandler.get_instance()
        self.con = self.lh.get_connection()
        self.uuid_entry = self.env.config.get("ldap.uuid_attribute", "entryUUID")

    def __del__(self):
        self.lh.free_connection(self.con)

    def loadAttrs(self, uuid, info):
        keys = info.keys()
        fltr_tpl = "%s=%%s" % self.uuid_entry
        fltr = ldap.filter.filter_format(fltr_tpl, [uuid])

        self.log.debug("searching with filter '%s' on base '%s'" % (fltr,
            self.lh.get_base()))
        res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE, fltr,
            keys)

        # Check if res is valid
        self.__check_res(uuid, res)

        #TODO: value conversation
        return dict((k,v) for k, v in res[0][1].iteritems() if k in keys)

    def dn2uuid(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_BASE, 'objectClass=*',
                [self.uuid_entry])[0][1][self.uuid_entry]

        # Check if res is valid
        self.__check_res(dn, res)

        return res[0]

    def __check_res(self, uuid, res):
        if not res:
            raise EntryNotFound("entry '%s' is not present" % uuid)

        if len(res) != 1:
            raise EntryNotUnique("entry '%s' is not unique" % uuid)
