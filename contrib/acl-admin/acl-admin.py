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
        """
        Helper method which converts a given scope value from int to string.

        =========== =============
        key         description
        =========== =============
        sid         The corresponding scope value
        =========== =============

        """
        acl_scope_map = {}
        acl_scope_map[ACL.ONE] = 'one'
        acl_scope_map[ACL.SUB] = 'sub'
        acl_scope_map[ACL.PSUB] = 'psub'
        acl_scope_map[ACL.RESET] = 'reset'

        if sid in acl_scope_map:
            return(acl_scope_map[sid])
        else:
            return("UNKNOWN")

    def strToScopeId(self, sid):
        """
        Helper method which converts a given scope value from string to int.

        =========== =============
        key         description
        =========== =============
        sid         The corresponding scope value
        =========== =============

        """
        acl_scope_map = {}
        acl_scope_map['one'] = ACL.ONE
        acl_scope_map['sub'] = ACL.SUB
        acl_scope_map['psub'] = ACL.PSUB
        acl_scope_map['reset'] = ACL.RESET

        if sid in acl_scope_map:
            return(acl_scope_map[sid])
        else:
            return(None)

    def printReportHeader(self, string):
        """
        Helper method which prints a header for reports.

        =========== =============
        key         description
        =========== =============
        string      The report caption.
        =========== =============

        """
        print
        print("-" * len(string))
        print(string)
        print("-" * len(string))

    def para_missing(self, name):
        """
        Helper method that shows a warning about a missing required parameter!

        =========== =============
        key         description
        =========== =============
        name        The name of the parameter that was missing.
        =========== =============

        """
        print
        print("<%s> parameter is missing!" % name)
        desc = self.get_para_help(name)
        if len(desc):
            for line in desc:
                print("      %s"  % line)

    def para_invalid(self, name):
        """
        Helper method which prints out a warning method that a parameter 
        was passend in an invalid format.

        =========== =============
        key         description
        =========== =============
        name        The name of the parameter we want to print the invalid message for.
        =========== =============
        """

        print
        print("<%s> parameter is invalid!" % name)
        desc = self.get_para_help(name)
        if len(desc):
            for line in desc:
                print("      %s"  % line)

    def get_para_help(self, para):
        """
        This method holds a description for all parameters that can be passed to this script.
        Due to the fact that we need the descriptions in several functions, i've put them
         into a single function.

        =========== =============
        key         description
        =========== =============
        para        The name of the parameter we want to get the description for.
        =========== =============
        """

        help_msgs = {
                "base":[
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

        # Return the help message, if it exists.
        if para in help_msgs:
            return(help_msgs[para])
        else:
            return(["no help for %s ..." % para])

    def get_value_from_args(self, name, args):
        """
        This method extracts a parameter out of a given argument-list.

        (Due to the fact that we need parameter values in several functions, i've put them
         into a single function)

        =========== =============
        key         description
        =========== =============
        para        The name of the parameter we want to get the value for.
        args        The arguments-list we want to extract from.
        =========== =============
        """

        # Validate the base value
        if name == "base":
            if len(args):
                base = args[0]
                del(args[0])
                return(base)
            else:
                self.para_missing('base')
                sys.exit(1)

        # Validate the scope value
        elif name == "scope":
            if len(args):
                if args[0] not in ['one', 'sub', 'psub', 'reset']:
                    self.para_invalid('scope')
                    sys.exit(1)
                else:
                    scope = args[0]
                    del(args[0])
                    return(scope)
            else:
                self.para_missing('scope')
                sys.exit(1)

        # Check for priority
        elif name == "priority":
            if len(args):
                try:
                    if int(args[0]) < -100 or int(args[0]) > 100:
                        self.para_invalid('priority')
                        sys.exit(1)
                except:
                    self.para_invalid('priority')
                    sys.exit(1)

                prio = int(args[0])
                del(args[0])
                return(prio)
            else:
                self.para_missing('priority')
                sys.exit(1)

        # Check action
        elif name == "action":
            if len(args):
                action = args[0]
                del(args[0])
                return(action)
            else:
                self.para_missing('action')
                sys.exit(1)

        # Check acls
        elif name == "acls":
            if len(args):
                acls = args[0]
                del(args[0])
                return(acls)
            else:
                self.para_missing('acl')
                sys.exit(1)

        # Check for options
        elif name == "options":
            if len(args):
                options = args[0]
                if not re.match(r"^([a-z0-9]*:[a-z0-9]*;)*$", options):
                    self.para_invalid('options')
                    sys.exit(1)

                del(args[0])
                return(options)
            return({})
        else:
            raise(Exception("Unknown parameter to extract: %s" %name))


    @helpDecorator("Adds a new ACL rule", "add acl <base> <scope> <priority> <action> <acls> [options]")
    def add_acl(self, args):
        """
        This method creates a new ACL rule depending on the passes arguments-list.

        (It can be accessed via parameter 'add acl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        base = self.get_value_from_args("base", args)
        scope = self.get_value_from_args("scope", args)
        priority = self.get_value_from_args("priority", args)
        action = self.get_value_from_args("action", args)
        acls = self.get_value_from_args("acls", args)
        options = self.get_value_from_args("options", args)

        print([base,scope,priority,action,acls,options])

        pass

    @helpDecorator("List all defined acls")
    def list_acls(self, args):
        """
        This method list all defined acls.

        (It can be accessed via parameter 'list acls')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
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
        This method list all defined acl roles.

        (It can be accessed via parameter 'list acls')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
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
    """
    This method prints out the command-line help for this script.
    """

    # Define cli-script parameters
    print(
        "\nAdministrate GOsa-ng permissions from the command line."
        "\n"
        "\nusage: acl-admin [-c CFGFILE] <list/add/update/remove> <acl/role> [parameters]"
        "\n"
        "\noptional arguments:"
        "\n  -c CFGFILE, --config CFGFILE"
        "\n    the agent-config file to use"
        "\n")

    for method in helpDecorator.method_list:
        sh = helpDecorator.method_list[method][0]
        lh = helpDecorator.method_list[method][1]
        method = re.sub("_"," ", method)
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
