# -*- coding: utf-8 -*-
import ldap
import ldap.dn
import ldap.filter
import ldap.schema
import ldap.modlist
import time
import datetime
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

    def load(self, uuid, info):
        keys = info.keys()
        fltr_tpl = "%s=%%s" % self.uuid_entry
        fltr = ldap.filter.filter_format(fltr_tpl, [uuid])

        self.log.debug("searching with filter '%s' on base '%s'" % (fltr,
            self.lh.get_base()))
        res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE, fltr,
            keys)

        # Check if res is valid
        self.__check_res(uuid, res)

        # Do value conversation
        items = dict((k,v) for k, v in res[0][1].iteritems() if k in keys)
        for key, value in items.items():
            cnv = getattr(self, "_convert_from_%s" % info[key].lower())
            lcnv = []
            for lvalue in items[key]:
                lcnv.append(cnv(lvalue))
            items[key] = lcnv

        return items

    def exists(self, misc):
        if self.is_uuid(misc):
            fltr_tpl = "%s=%%s" % self.uuid_entry
            fltr = ldap.filter.filter_format(fltr_tpl, [misc])

            res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE,
                    fltr, [self.uuid_entry])

        else:
            res = self.con.search_s(misc, ldap.SCOPE_ONELEVEL, '(objectClass=*)',
                [self.uuid_entry])

        if not res:
            return False

        return len(res) == 1

    def remove(self, uuid, recursive=False):
        dn = self.dn2uuid(uuid)

        if recursive:
            self.__delete_children(dn)

        else:
            self.con.delete_s(dn)

    def __delete_children(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_ONELEVEL, '(objectClass=*)',
                [self.uuid_entry])

        for c_dn, entry in res:
            self.__delete_children(c_dn)

        # Delete ourselves
        self.con.delete_s(dn)

#    def retract(self, uuid):
#        pass

#    def create(self, base, data):
#        pass

#    def extend(self, base, data):
#        pass

    def update(self, uuid, data):

        # Load DN for entry and assemble a proper modlist
        dn = self.uuid2dn(uuid)

        print "="*80
        print "Resolved to DN:", dn
        print "-"*80

        mod_attrs = []
        for attr, entry in data.iteritems():

            # Value removed?
            if entry['orig'] and not entry['value']:
                print "- %s" % attr
                mod_attrs.append((ldap.MOD_DELETE, attr, None))
                continue

            cnv = getattr(self, "_convert_to_%s" % entry['type'].lower())
            items = []
            for lvalue in entry['value']:
                items.append(cnv(lvalue))

            # New value?
            if not entry['orig'] and entry['value']:
                print "+ %s: %s" % (attr, items)
                mod_attrs.append((ldap.MOD_ADD, attr, items))
                continue

            # Ok, modified...
            mod_attrs.append((ldap.MOD_REPLACE, attr, items))
            print "~ %s: %s" % (attr, items)

        print "-"*80

        # Did we change one of the RDN attributes?
        new_rdn_parts = []
        rdns = ldap.dn.str2dn(dn, flags=ldap.DN_FORMAT_LDAPV3)
        rdn_parts = rdns[0]

        for attr, value, idx in rdn_parts:
            if attr in data:
                cnv = getattr(self, "_convert_to_%s" % data[attr]['type'].lower())
                new_rdn_parts.append((attr, cnv(data[attr]['value'][0]), 4))
            else:
                new_rdn_parts.append((attr, value, idx))

        # Build new target DN and check if it has changed...
        tdn = ldap.dn.dn2str([new_rdn_parts] + rdns[1:])
        if tdn != dn:
            self.con.rename_s(dn, ldap.dn.dn2str([new_rdn_parts]))

        # Write back...
        self.con.modify_s(tdn, mod_attrs)

        print "="*80

    def uuid2dn(self, uuid):
        # Get DN of entry
        fltr_tpl = "%s=%%s" % self.uuid_entry
        fltr = ldap.filter.filter_format(fltr_tpl, [uuid])

        self.log.debug("searching with filter '%s' on base '%s'" % (fltr,
            self.lh.get_base()))
        res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE, fltr,
                [self.uuid_entry])

        self.__check_res(uuid, res)

        return res[0][0]

    def dn2uuid(self, dn):
        res = self.con.search_s(dn.encode('utf-8'), ldap.SCOPE_BASE, '(objectClass=*)',
                [self.uuid_entry])

        # Check if res is valid
        self.__check_res(dn, res)

        return res[0][1][self.uuid_entry][0]

    def __check_res(self, uuid, res):
        if not res:
            raise EntryNotFound("entry '%s' is not present" % uuid)

        if len(res) != 1:
            raise EntryNotUnique("entry '%s' is not unique" % uuid)

    def _convert_from_boolean(self, value):
        return value == "TRUE"

    def _convert_from_string(self, value):
        return str(value)

    def _convert_from_unicodestring(self, value):
        return unicode(value.decode('utf-8'))

    def _convert_from_integer(self, value):
        return int(value)

    def _convert_from_timestamp(self, value):
        return datetime.datetime.strptime(value, "%Y%m%d%H%M%SZ")

    def _convert_from_date(self, value):
        ts = time.mktime(time.strptime(value, "%Y%m%d%H%M%SZ"))
        return datetime.date.fromtimestamp(ts)

    def _convert_from_binary(self, value):
        return value

    def _convert_to_boolean(self, value):
        return "TRUE" if value else "FALSE"

    def _convert_to_string(self, value):
        return str(value)

    def _convert_to_unicodestring(self, value):
        return str(value.encode('utf-8'))

    def _convert_to_integer(self, value):
        return int(value)

    def _convert_to_timestamp(self, value):
        return value.strftime("%Y%m%d%H%M%SZ")

    def _convert_to_date(self, value):
        return value.strftime("%Y%m%d%H%M%SZ")

    def _convert_to_binary(self, value):
        return value
