#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from gosa.agent.acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver, ACLException
from gosa.common import Environment
import sys
import gettext
_ = gettext.gettext

#import os
#import re
#import grp
#import pynotify
#import gobject
#import dbus.mainloop.glib
#import time
#import pwd
#import getpass
#import signal


class ACLAdmin(object):
    def __init__(self, cfgFile):
        Environment.noargs = True
        Environment.config = cfgFile
        self.env = Environment.getInstance()
        self.resolver = ACLResolver()
        self.ldap_base = self.resolver.base

    def idToScopeStr(self, sid):
        acl_scope_map = {}
        acl_scope_map[ACL.ONE] = 'one'
        acl_scope_map[ACL.SUB] = 'sub'
        acl_scope_map[ACL.PSUB] = 'psub'
        acl_scope_map[ACL.RESET] = 'reset'

        if sid in acl_scope_map:
            return(acl_scope_map[sid])
        else:
            return("UNKNOWN")

    def printReportHeader(self, string):
        print
        print("-" * len(string))
        print(string)
        print("-" * len(string))

    def listAcls(self):
        self.printReportHeader(_("Listing of active GOsa-ng acls"))
        allSets = self.resolver.list_acls()
        if not len(allSets):
            print("   ... none")
        for aclset in allSets:
            for acl in aclset:
                print("ID: %i \tBASE: %s \t SCOPE (%s)" % (acl.id, aclset.base, self.idToScopeStr(acl.scope)))
                print("       \tMEMBER: %s" % (" ".join(acl.members)))
                if acl.uses_role:
                    print("\trefers to role: %s" % acl.role)
                else:
                    cnt = 1
                    print("     \tACTIONS:")
                    for action in acl.actions:
                        print("        - %s. %s (%s)  %s" % (cnt, action['topic'], action['acls'], action['options']))
                        cnt += 1

    def listRoles(self):
        self.printReportHeader(_("Listing of active GOsa-ng roles"))
        allRoles = self.resolver.list_roles()
        if not len(allRoles):
            print("   ... none")
        for aclrole in allRoles:
            for acl in aclrole:
                print("ID: %i \tROLENAME: %s \t SCOPE (%s)" % (acl.id, aclset.name, self.idToScopeStr(acl.scope)))
                if acl.uses_role:
                    print("\trefers to role: %s" % acl.role)
                else:
                    cnt = 1
                    print("     \tACTIONS:")
                    for action in acl.actions:
                        print("        - %s. %s (%s)  %s" % (cnt, action['topic'], action['acls'], action['options']))
                        cnt += 1
def main():

    # Define cli-script parameters
    parser = argparse.ArgumentParser(description="Administrate GOsa-ng permissions from the command line.",
            prog="acl-admin")

    parser.add_argument("-c", "--config", default="/etc/gosa/config", dest="cfgFile", help=_("the agent-config file to use"))
    parser.add_argument("-l", dest="listAcls", action="store_true", help=_("shows a list of all defined acls"))
    parser.add_argument("-r", dest="listRoles", action="store_true", help=_("shows a list of defined acl-roles"))

    # Check if at least 'message' and 'title' are given.
    my_args = parser.parse_args()
    if my_args.listAcls:
        r = ACLAdmin(my_args.cfgFile)
        r.listAcls()
    if my_args.listRoles:
        r = ACLAdmin(my_args.cfgFile)
        r.listRoles()

if __name__ == '__main__':
    main()
