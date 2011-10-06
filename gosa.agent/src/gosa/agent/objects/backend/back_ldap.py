# -*- coding: utf-8 -*-
import ldap
import ldap.dn
import ldap.filter
import ldap.schema
import ldap.modlist
import time
import datetime
from itertools import permutations
from logging import getLogger
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler
from gosa.agent.objects.backend import ObjectBackend, EntryNotFound, EntryNotUnique


class RDNNotSpecified(Exception):
    pass


class DNGeneratorError(Exception):
    pass


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

    def identify(self, dn, params):
        ocs = ["(objectClass=%s)" % o.strip() for o in params['objectClasses'].split(",")]
        fltr = "(&" + "".join(ocs) + ")"
        res = self.con.search_s(dn.encode('utf-8'), ldap.SCOPE_BASE, fltr,
                [self.uuid_entry])

        return len(res) == 1

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
        dn = self.uuid2dn(uuid)

        if recursive:
            return self.__delete_children(dn)

        else:
            self.log.debug("removing entry '%s'" % dn)
            return self.con.delete_s(dn)

    def __delete_children(self, dn):
        res = self.con.search_s(dn, ldap.SCOPE_ONELEVEL, '(objectClass=*)',
                [self.uuid_entry])

        for c_dn, entry in res:
            self.__delete_children(c_dn)

        # Delete ourselves
        self.log.debug("removing entry '%s'" % dn)
        return self.con.delete_s(dn)

    def retract(self, uuid, data, params):
        # Remove defined data from the specified object
        dn = self.uuid2dn(uuid)
        mod_attrs = []

        # We know about object classes - remove them
        if 'objectClasses' in params:
            ocs = [o.strip() for o in params['objectClasses'].split(",")]
            mod_attrs.append((ldap.MOD_DELETE, 'objectClass', ocs))

        # Remove all other keys related to this object
        for key in data:
            mod_attrs.append((ldap.MOD_DELETE, key, None))

        self.con.modify_s(dn, mod_attrs)

    def extend(self, uuid, data, params, foreign_keys):
        dn = self.uuid2dn(uuid)
        return self.create(dn, data, params, foreign_keys)

    def move_extension(self, uuid, new_base):
        # There is no need to handle this inside of the LDAP backend
        pass

    def move(self, uuid, new_base):
        dn = self.uuid2dn(uuid)
        self.log.debug("moving entry '%s' to new base '%s'" % (dn, new_base))
        rdn = ldap.dn.explode_dn(dn, flags=ldap.DN_FORMAT_LDAPV3)[0]
        return self.con.rename_s(dn, rdn, new_base)

    def create(self, base, data, params, foreign_keys=None):
        mod_attrs = []
        self.log.debug("gathering modifications for entry on base '%s'" % base)
        for attr, entry in data.iteritems():

            # Skip foreign keys
            if foreign_keys and attr in foreign_keys:
                continue

            cnv = getattr(self, "_convert_to_%s" % entry['type'].lower())
            items = []
            for lvalue in entry['value']:
                items.append(cnv(lvalue))

            self.log.debug(" * add attribute '%s' with value %s" % (attr, items))
            if foreign_keys == None:
                mod_attrs.append((attr, items))
            else:
                mod_attrs.append((ldap.MOD_ADD, attr, items))

        # We know about object classes - add them if possible
        if 'objectClasses' in params:
            ocs = [o.strip() for o in params['objectClasses'].split(",")]
            if foreign_keys == None:
                mod_attrs.append(('objectClass', ocs))
            else:
                mod_attrs.append((ldap.MOD_ADD, 'objectClass', ocs))

        if foreign_keys == None:
            # Check if obligatory information for assembling the DN are
            # provided
            if not 'RDN' in params:
                raise RDNNotSpecified("there is no 'RDN' backend parameter specified")

            # Build unique DN using maybe optional RDN parameters
            rdns = [d.strip() for d in params['RDN'].split(",")]
            dn = self.get_uniq_dn(rdns, base, data).encode("utf-8")
            if not dn:
                raise DNGeneratorError("no unique DN available on '%' using: %s" % (base, ",".join(rdns)))

        else:
            dn = base

        self.log.debug("evaulated new entry DN to '%s'" % dn)

        # Write...
        self.log.debug("saving entry '%s'" % dn)

        if foreign_keys == None:
            self.con.add_s(dn, mod_attrs)
        else:
            self.con.modify_s(dn, mod_attrs)

        # Return automatic uuid
        return self.dn2uuid(dn)

    def update(self, uuid, data):

        # Assemble a proper modlist
        dn = self.uuid2dn(uuid)

        mod_attrs = []
        self.log.debug("gathering modifications for entry '%s'" % dn)
        for attr, entry in data.iteritems():

            # Value removed?
            if entry['orig'] and not entry['value']:
                self.log.debug(" * remove attribute '%s'" % attr)
                mod_attrs.append((ldap.MOD_DELETE, attr, None))
                continue

            cnv = getattr(self, "_convert_to_%s" % entry['type'].lower())
            items = []
            for lvalue in entry['value']:
                items.append(cnv(lvalue))

            # New value?
            if not entry['orig'] and entry['value']:
                self.log.debug(" * add attribute '%s' with value %s" % (attr, items))
                mod_attrs.append((ldap.MOD_ADD, attr, items))
                continue

            # Ok, modified...
            self.log.debug(" * replace attribute '%s' with value %s" % (attr, items))
            mod_attrs.append((ldap.MOD_REPLACE, attr, items))

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
            self.log.debug("entry needs a rename from '%s' to '%s'" % (dn, tdn))
            self.con.rename_s(dn, ldap.dn.dn2str([new_rdn_parts]))

        # Write back...
        self.log.debug("saving entry '%s'" % tdn)
        return self.con.modify_s(tdn, mod_attrs)

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

    def get_uniq_dn(self, rdns, base, data):
        try:
            for dn in self.build_dn_list(rdns, base, data):
                res = self.con.search_s(dn.encode('utf-8'), ldap.SCOPE_BASE, '(objectClass=*)',
                    [self.uuid_entry])

        except ldap.NO_SUCH_OBJECT:
            return dn

        return None

    def is_uniq(self, attr, value, at_type):
        fltr_tpl = "%s=%%s" % attr

        cnv = getattr(self, "_convert_to_%s" % at_type.lower())
        value = cnv(value)
        fltr = ldap.filter.filter_format(fltr_tpl, [value])

        self.log.debug("uniq test with filter '%s' on base '%s'" % (fltr,
            self.lh.get_base()))
        res = self.con.search_s(self.lh.get_base(), ldap.SCOPE_SUBTREE, fltr,
            [self.uuid_entry])

        return len(res) == 0

    def build_dn_list(self, rdns, base, data):
        fix = rdns[0]
        var = rdns[1:] if len(rdns) > 1 else []
        dns = [fix]

        # Bail out if fix part is not in data
        if not fix in data:
            raise DNGeneratorError("fix attribute '%s' is not in the entry" % fix)

        # Append possible variations of RDN attributes
        if var:
            for rdn in permutations(var + [None] * (len(var) - 1), len(var)):
                dns.append("%s,%s" % (fix, ",".join(filter(lambda x: x and x in data and data[x], list(rdn)))))
        dns = list(set(dns))

        # Assemble DN of RDN combinations
        dn_list = []
        for t in [tuple(d.split(",")) for d in dns]:
            ndn = []
            for k in t:
                ndn.append("%s=%s" % (k, ldap.dn.escape_dn_chars(data[k]['value'][0])))
            dn_list.append("+".join(ndn) + "," + base)

        return sorted(dn_list, key=len)

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
        return str(value)

    def _convert_to_timestamp(self, value):
        return value.strftime("%Y%m%d%H%M%SZ")

    def _convert_to_date(self, value):
        return value.strftime("%Y%m%d%H%M%SZ")

    def _convert_to_binary(self, value):
        return value
