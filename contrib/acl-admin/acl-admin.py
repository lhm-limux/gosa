#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from gosa.agent.acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver, ACLException
from gosa.common import Environment
import sys
import inspect
import gettext
import re
import copy

_ = gettext.gettext

class helpDecorator(object):
    largeHelp = ""
    smallHelp = ""
    method_list = {}

    def __init__(self, smallHelp, largeHelp=""):
        self.smallHelp = smallHelp
        self.largeHelp = largeHelp

    def __call__(self, f):
        helpDecorator.method_list[f.__name__] = (self.smallHelp, self.largeHelp)
        return f


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

    def para_missing(self, name):
        print
        print("<%s> parameter is missing!" % name)
        desc = self.get_para_help(name)
        if len(desc):
            for line in desc:
                print("      %s"  % line)

    def para_invalid(self, name):
        print
        print("<%s> parameter is invalid!" % name)
        desc = self.get_para_help(name)
        if len(desc):
            for line in desc:
                print("      %s"  % line)

    def get_para_help(self, para):

        help_msgs = {"base":[
                    "The base parameter specifies the position acls are active for",
                    "For example: dc=example,dc=de"],
                "scope":[
                    "Possible scope values are",
                    " one   - For acls that are active only for the current base",
                    "         this can be revoked using the 'reset' scope!",
                    " sub   - For acls that are active only for the complete subtree",
                    "         this can be revoked using the 'reset' scope!",
                    " psub  - For acls that are active only for the complete subtree",
                    "         this can NOT be revoked using the 'reset' scope!",
                    " reset - Revokes previously defined acls, except for those with scope 'psub'"]
                }
        if para in help_msgs:
            return(help_msgs[para])
        else:
            return(["no help for %s ..." % para])

    @helpDecorator("Adds a new ACL rule", "add acl <base> <scope> <priority> <action> <acls> [options]")
    def add_acl(self, args):

        # Validate given parameters

        # Validate the base value
        if len(args):
            base = args[0]
            del(args[0])
        else:
            self.para_missing('base')
            sys.exit(1)

        # Validate the scope value
        if len(args):
            if args[0] not in ['one', 'sub', 'psub', 'reset']:
                self.para_invalid('scope')
                sys.exit(1)
            else:
                scope = args[0]
                del(args[0])
        else:
            self.para_missing('scope')
            sys.exit(1)

        # Check for priority
        if len(args):
            try:
                if int(args[0]) < -100 or int(args[0]) > 100:
                    self.para_invalid('priority')
                    sys.exit(1)
            except:
                self.para_invalid('priority')
                sys.exit(1)

            scope = int(args[0])
            del(args[0])
        else:
            self.para_missing('priority')
            sys.exit(1)

        # Check action
        if len(args):
            action = args[0]
            del(args[0])
        else:
            self.para_missing('action')
            sys.exit(1)

        # Check acls
        if len(args):
            acls = args[0]
            del(args[0])
        else:
            self.para_missing('acl')
            sys.exit(1)

        # Check for options
        if len(args):
            options = args[0]
            if not re.match(r"^([a-z0-9]*:[a-z0-9]*;)*$", options):
                self.para_invalid('options')
                sys.exit(1)

            del(args[0])

    @helpDecorator("List all defined acls")
    def list_acls(self, args):
        """
        List all defined acls.
        """

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

    @helpDecorator("List all defined roles")
    def list_roles(self, args):
        """
        List all defined roles.
        """
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


def print_help():

    # Define cli-script parameters
    print("""
Administrate GOsa-ng permissions from the command line.

usage: acl-admin [-c CFGFILE] <list/add/update/remove> <acl/role> [parameters]

optional arguments:
  -c CFGFILE, --config CFGFILE
    the agent-config file to use

Actions:""")

    for method in helpDecorator.method_list:
        sh = helpDecorator.method_list[method][0]
        lh = helpDecorator.method_list[method][1]
        if lh != "":
            print("  %s %s\n    %s\n" % (method.ljust(20), sh, lh))
        else:
            print("  %s %s" % (method.ljust(20), sh))

def main():

    if "-h" in sys.argv: 
        print_help()
        sys.exit(0)

    # Predefine some values
    cfgFile = "/etc/gosa/config"

    # Parse out config parameter
    my_args = sys.argv
    if "-c" in my_args or "--config" in my_args:
        if "-c" in my_args:
            pos = my_args.index("-c")
        if "--config" in my_args:
            pos = my_args.index("--config")

        if len(my_args)-1 <= pos:
            print(_("Missing config file parameter!"))
            sys.exit(1)
        else:
            cfgFile = my_args[pos]
            del(my_args[pos])
            del(my_args[pos])

    # Remove the first element of my_args, we don't need it.
    del(my_args[0])

    # If no args were given print the help message and quit
    if len(my_args) == 0:
        print_help()
        sys.exit(1)

    # Check if there is a method which is using the decorator 'helpDecorator' and
    # is matching the given parameters
    method = ""
    called = False
    args_left = copy.deepcopy(my_args)
    while(len(args_left)):
        method += "_" + args_left[0]
        del(args_left[0])

        method = re.sub(r"^_", "", method)
        if method in helpDecorator.method_list:
            a = ACLAdmin(cfgFile)
            ret = getattr(a, method)(args_left)
            called = True

    if not called:
        print("Invalid argument list: %s" % (" ".join(my_args)))
        print_help()
        sys.exit(1)




if __name__ == '__main__':
    main()
