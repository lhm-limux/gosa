#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler

import ldap
import ldap.filter

class FAI(object):
    def __init__(self):
        self.env = Environment.getInstance()
        self.ldap_handler = LDAPHandler.get_instance()
        self.nfs_root= self.env.config.get('nfs_root', default = '/srv/nfsroot')
        self.nfs_opts= self.env.config.get('nfs_opts', default = 'nfs4')
        self.fai_flags= self.env.config.get('fai_flags', default = 'verbose,sshd,syslogd,createvt,reboot')
        self.union= self.env.config.get('union', default = 'unionfs')

    def getBootParams(self, address):
        result = None
        with self.ldap_handler.get_handle() as ldap_connection:
            res = ldap_connection.search_s(
                self.ldap_handler.get_base(),
                ldap.SCOPE_SUBTREE,
                ldap.filter.filter_format("(&(macAddress=%s)(objectClass=FAIobject))", [address]),
                [ 'FAIstate', 'gotoBootKernel', 'gotoKernelParameters', 'gotoLdapServer', 'cn', 'ipHostNumber' ])
            if res.count()==0:
                result = "localboot"
            elif res.count()>1:
                self.env.log.error("{address} - MAC lookup error: too many LDAP results ({count})".format(address=address, count=res.count()))
            else:
                self.env.log.info("No FAI configuration for client with MAC {address}".format(address=address))
        return result

    def getInfo(self):
        return "FAI - Fully Automatic Installation"


#FAI().systemGetBootParams("00:06:29:1F:75:95")
