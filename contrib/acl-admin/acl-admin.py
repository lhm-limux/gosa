#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import sys
import copy
import gettext
import argparse
from gosa.agent.acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver, ACLException
from gosa.common import Environment

_ = gettext.gettext


class helpDecorator(object):
    """
    A method decoratot which allows to mark those methods that can be used
    as script parameters.

    e.g.
        @helpDecorator(_("Short help msg"), _("A longer help message"))

    """
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
    """
    This class privides all necessary action for the 'acl-admin' script.

    All script actions will be forwarded to exported gosa commands.
    """

    acl_scope_map = {
        'one': ACL.ONE,
        'sub': ACL.SUB,
        'psub': ACL.PSUB,
        'reset': ACL.RESET,
        }

    def __init__(self, cfgFile):
        Environment.noargs = True
        Environment.config = cfgFile
        self.env = Environment.getInstance()
        self.resolver = ACLResolver()
        self.ldap_base = self.resolver.base

        # Tell the resolver to ignore acls for us (temporarily)
        self.resolver.admins.append('tmp_admin')

        # Build reverse scope map
        self.rev_acl_scope_map = dict((v, k) for k, v in
                self.acl_scope_map.iteritems())

    def idToScopeStr(self, sid):
        """
        Helper method which converts a given scope value from int to string.

        =========== =============
        key         description
        =========== =============
        sid         The corresponding scope value
        =========== =============

        """
        if sid in self.rev_acl_scope_map:
            return(self.rev_acl_scope_map[sid])
        else:
            return(_("unknown"))

    def strToScopeId(self, sid):
        """
        Helper method which converts a given scope value from string to int.

        =========== =============
        key         description
        =========== =============
        sid         The corresponding scope value
        =========== =============

        """
        if sid in self.acl_scope_map:
            return(self.acl_scope_map[sid])
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
        print(_("<%s> parameter is missing!") % name)
        desc = self.get_para_help(name)
        if len(desc):
            print " %s" % desc

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
        print(_("<%s> parameter is invalid!") % name)
        desc = self.get_para_help(name)
        if len(desc):
            print " %s" % desc

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
                "base": _("The base parameter specifies the position acls are active for. For example: dc=example,dc=de"),
                "scope": _("The scope value specifies how the acl role influences sub-directories"
                    "\n Possible scope values are:"
                    "\n  one   - For acls that are active only for the current base"
                    "\n          this can be revoked using the 'reset' scope!"
                    "\n  sub   - For acls that are active only for the complete subtree"
                    "\n          this can be revoked using the 'reset' scope!"
                    "\n  psub  - For acls that are active only for the complete subtree"
                    "\n          this can NOT be revoked using the 'reset' scope!"
                    "\n  reset - Revokes previously defined acls, except for those with scope 'psub'"),
                "priority": _("An integer value to prioritize an acl-rule. (Lower values mean higher priority)"
                    "\n  highest priority: -100"
                    "\n  lowest priority: -100"),
                "members": _("The names of the users/clients the acl-rule should be valid for. "
                    "\n  A comma separated list:"
                    "\n   e.g.: hubert,peter,klaus"),
                "acl-definition": _("The <acl-defintion> parameter specifies what actions can be performed on a given topic."
                    "\n"
                    "\n Syntax {<topic>:<acls>:<option1>: ... :<option N>,}"
                    "\n"
                    "\n <topic> "
                    "\n ========"
                    "\n The topic defines the target-action this acl includes"
                    "\n Topics can contain placeholder to be more flexible when it come to resolving acls."
                    "\n You can use `#` and `*` where `#` matches for one level and `*` for multiple topic levels."
                    "\n  e.g.: "
                    "\n   org.gosa.*        for all topics included in org.gosa"
                    "\n   org.gosa.#.help   allows to call help methods for modules under org.gosa"
                    "\n"
                    "\n <acls>"
                    "\n ======"
                    "\n The acl parameter defines which operations can be executed on a given topic."
                    "\n  e.g.:"
                    "\n   rwcd    -> allows to read, write, create and delete"
                    "\n"
                    "\n  Possible values are:"
                    "\n    r - Read             w - Write           m - Move"
                    "\n    c - Create           d - Delete          s - Search - or beeing found"
                    "\n    x - Execute          e - Receive event"
                    "\n"
                    "\n <options>"
                    "\n ========="
                    "\n Options are additional checks, please read the GOsa documentation for details."
                    "\n The format is:  key:value;key:value;..."
                    "\n  e.g. (Do not forget to use quotes!)"
                    "\n   'uid:peter;eventType:start;'"
                    "\n"
                    "\n Command examples:"
                    "\n   A single definition without options:"
                    "\n       org.gosa.*:rwcdm"
                    "\n"
                    "\n   A single definition with options:"
                    "\n       org.gosa.*:rwcdm:uid=user_*:tag=event"
                    "\n"
                    "\n   A multi action defintion"
                    "\n       org.gosa.events:rwcdm,org.gosa.factory:rw,org.gosa.something:rw"
                    "\n"),
                "topic": _("The topic defines the target-action this acl includes"
                    "\n Topics can contain placeholder to be more flexible when it come to resolving acls."
                    "\n You can use `#` and `*` where `#` matches for one level and `*` for multiple topic levels."
                    "\n  e.g.: "
                    "\n   org.gosa.*        for all topics included in org.gosa"
                    "\n   org.gosa.#.help   allows to call help methods for modules under org.gosa"),
                "acl": _("The acl parameter defines which operations can be executed on a given topic."
                    "\n  e.g.:"
                    "\n   rwcd    -> allows to read, write, create and delete"
                    "\n"
                    "\n  Possible values are:"
                    "\n    * r - Read"
                    "\n    * w - Write"
                    "\n    * m - Move"
                    "\n    * c - Create"
                    "\n    * d - Delete"
                    "\n    * s - Search - or beeing found"
                    "\n    * x - Execute"
                    "\n    * e - Receive event"),
                "options": _("Options are additional checks, please read the GOsa documentation for details."
                    "\n The format is:  key:value;key:value;..."
                    "\n  e.g. (Do not forget to use quotes!)"
                    "\n   'uid:peter;eventType:start;'"),
                "id": _("ID parameters have to be of type int!"),
                "rolename": _("The name of the acl role you want to set"),
                "acl-update-action": _("You can specify the upate-action for the acl."
                    "\n  Possible values are:"
                    "\n    * set-scope      Update the scope of an acl-rule"
                    "\n    * set-members    Set a new list of members for an acl-rule"
                    "\n    * set-priority   Set another priority level for the acl-rule"
                    "\n    * set-action     Set a new action for the acl"
                    "\n    * set-role       Let the acl-rule point to a role"),
                "roleacl-update-action": _("You can specify the upate-action for the role-acl."
                    "\n  Possible values are:"
                    "\n    * set-scope      Update the scope of an acl-rule"
                    "\n    * set-priority   Set another priority level for the acl-rule"
                    "\n    * set-action     Set a new action for the acl"
                    "\n    * set-role       Let the acl-rule point to a role"),
                "acl-add-action": _("You can either create acl-rule that contain direkt permissions settings"
                    " or you can use previously defined roles"
                    "\n  Possible values are:"
                    "\n    * with-actions   To directly specify the topic, acls and options this defintions includes"
                    "\n    * with-role      To use a rolename instead of defining actions directly")}

        # Return the help message, if it exists.
        if para in help_msgs:
            return(help_msgs[para])
        else:
            return(_("no help for %s ...") % para)

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

        # Validate given id-parameters
        if name in ["id"]:
            if len(args):
                try:
                    if int(args[0]) < -100 or int(args[0]) > 100:
                        self.para_invalid(name)
                        sys.exit(1)
                except KeyError:
                    self.para_invalid(name)
                    sys.exit(1)
                aid = int(args[0])
                del(args[0])
                return(aid)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Validate the base value
        elif name == "base":
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
                if args[0] not in self.acl_scope_map:
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
                except Exception:
                    self.para_invalid('priority')
                    sys.exit(1)

                prio = int(args[0])
                del(args[0])
                return(prio)
            else:
                self.para_missing('priority')
                sys.exit(1)

        # Check topic
        elif name == "topic":
            if len(args):
                topic = args[0]
                del(args[0])
                return(topic)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check topic
        elif name == "acl-definition":
            if len(args):
                topic = args[0]
                del(args[0])
                return(topic)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check members
        elif name == "members":
            if len(args):
                members = args[0]
                del(args[0])

                # Validate the found member valus
                members = members.split(",")
                m_list = []
                for member in members:
                    member = member.strip()
                    if not re.match("^[a-zA-Z][a-zA-Z0-9\.-]*$", member):
                        self.para_invalid(name)
                        sys.exit(1)
                    m_list.append(member)
                return(m_list)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check acls
        elif name == "acls":
            if len(args):
                acls = args[0]
                del(args[0])
                return(acls)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check rolename
        elif name == "rolename":
            if len(args):
                rolename = args[0]
                del(args[0])
                return(rolename)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check for options
        elif name == "options":
            if len(args):
                options = args[0]
                if not re.match(r"^([a-z0-9]*:[^:;]*;)*$", options):
                    self.para_invalid('options')
                    sys.exit(1)

                opts = {}
                for item in options.split(";"):
                    if len(item):
                        tmp = item.split(":")
                        opts[tmp[0]] = tmp[1]

                del(args[0])
                return(opts)
            return({})

        # Check for acl-update-actions
        elif name == "acl-update-action":
            if len(args):
                action = args[0]
                if action not in ["set-scope", "set-members", "set-priority", "set-action", "set-role"]:
                    self.para_invalid(name)
                    sys.exit(1)

                del(args[0])
                return(action)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check for roleacl-update-actions
        elif name == "roleacl-update-action":
            if len(args):
                action = args[0]
                if action not in ["set-scope", "set-priority", "set-action", "set-role"]:
                    self.para_invalid(name)
                    sys.exit(1)

                del(args[0])
                return(action)
            else:
                self.para_missing(name)
                sys.exit(1)

        # Check for acl-add-actions
        elif name == "acl-add-action":
            if len(args):
                action = args[0]
                if action not in ["with-actions", "with-role"]:
                    self.para_invalid(name)
                    sys.exit(1)

                del(args[0])
                return(action)
            else:
                self.para_missing(name)
                sys.exit(1)

        else:
            raise(Exception("Unknown parameter to extract: %s" % (name,)))

    @helpDecorator(_("Updates an acl entry"), _("update acl [set-scope|set-members|set-priority|set-action|set-role] <ID> [parameters]"))
    def update_acl(self, args):
        """
        This method updates an existing ACL-rule

        (It can be accessed via parameter 'update acl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        action_type = self.get_value_from_args("acl-update-action", args)
        aid = self.get_value_from_args("id", args)

        try:
            if "set-scope" == action_type:
                scope = self.get_value_from_args("scope", args)
                self.resolver.updateACL('tmp_admin', aid, scope=scope)
                self.resolver.save_to_file()

            if "set-members" == action_type:
                members = self.get_value_from_args("members", args)
                self.resolver.updateACL('tmp_admin', aid, members=members)
                self.resolver.save_to_file()

            if "set-priority" == action_type:
                priority = self.get_value_from_args("priority", args)
                self.resolver.updateACL('tmp_admin', aid, priority=priority)
                self.resolver.save_to_file()

            if "set-action" == action_type:
                scope = self.get_value_from_args("scope", args)
                topic = self.get_value_from_args("topic", args)
                acls = self.get_value_from_args("acls", args)
                options = self.get_value_from_args("options", args)
                actions = [{'topic': topic, 'acls': acls, 'options': options}]
                self.resolver.updateACL('tmp_admin', aid, actions=actions, scope=scope)
                self.resolver.save_to_file()

            if "set-role" == action_type:
                rolename = self.get_value_from_args("rolename", args)
                self.resolver.updateACL('tmp_admin', aid, rolename=rolename)
                self.resolver.save_to_file()

        except ACLException as e:
            print e

    @helpDecorator(_("Removes an acl entry"), _("remove acl <ID>"))
    def remove_acl(self, args):
        """
        This method removes an ACL-rule entry by ID.

        (It can be accessed via parameter 'remove acl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """
        rid = self.get_value_from_args("id", args)
        try:
            self.resolver.removeACL('tmp_admin', rid)
            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Adds a new acl entry"), _("add acl [with-role|with-actions] <base> <priority> <members> [rolename|<scope> <topic> <acls> [options]]"))
    def add_acl(self, args):
        """
        This method creates a new ACL rule

        (It can be accessed via parameter 'add acl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        try:
            action_type = self.get_value_from_args("acl-add-action", args)
            actions = rolename = scope = members = None
            base = self.get_value_from_args("base", args)
            priority = self.get_value_from_args("priority", args)
            members = self.get_value_from_args("members", args)

            # Do we create an acl with direct actions or do we use a role.
            if action_type == "with-actions":
                scope = self.get_value_from_args("scope", args)
                actions = self.get_value_from_args("acl-definition", args)
                #topic = self.get_value_from_args("topic", args)
                #acls = self.get_value_from_args("acls", args)
                #options = self.get_value_from_args("options", args)
                #actions = [{'topic': topic, 'acls': acls, 'options': options}]
                #self.resolver.addACL('tmp_admin', base, priority, members, actions=actions, scope=scope)

                print actions
            else:
                rolename = self.get_value_from_args("rolename", args)
                self.resolver.addACL('tmp_admin', base, priority, members, rolename=rolename)

            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Adds a new acl entry to an existing role"), _("add roleacl [with-role|with-actions] <rolename> <priority> [rolename|<scope> <topic> <acls> [options]]"))
    def add_roleacl(self, args):
        """
        This method creates a new ACLRole entry for a given role.

        (It can be accessed via parameter 'add roleacl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        try:
            action_type = self.get_value_from_args("acl-add-action", args)
            actions = rolename = scope = members = None
            rolename = self.get_value_from_args("rolename", args)
            priority = self.get_value_from_args("priority", args)

            # Do we create an acl with direct actions or do we use a role.
            if action_type == "with-actions":
                scope = self.get_value_from_args("scope", args)
                topic = self.get_value_from_args("topic", args)
                acls = self.get_value_from_args("acls", args)
                options = self.get_value_from_args("options", args)
                actions = [{'topic': topic, 'acls': acls, 'options': options}]
                self.resolver.addACLToRole('tmp_admin', rolename, priority, actions=actions, scope=scope)
            else:
                use_role = self.get_value_from_args("rolename", args)
                self.resolver.addACLToRole('tmp_admin', rolename, priority, use_role=use_role)

            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Adds a new role"), _("add role <rolename>"))
    def add_role(self, args):
        """
        This method creates a new ACL ROLE

        (It can be accessed via parameter 'add role')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        rolename = self.get_value_from_args("rolename", args)
        try:
            self.resolver.addACLRole('tmp_admin', rolename)
            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Removes an acl entry from a role"), _("remove roleacl <ID>"))
    def remove_roleacl(self, args):
        """
        This method removes an ACL from an ROLE

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        aid = self.get_value_from_args("id", args)
        try:
            self.resolver.removeRoleACL('tmp_admin', aid)
            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Removes a role"), _("remove role <rolename>"))
    def remove_role(self, args):
        """
        This method removes an ACLRole

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        rolename = self.get_value_from_args("rolename", args)
        try:
            self.resolver.removeRole('tmp_admin', rolename)
            self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("Updates an acl entry of a role"), _("update roleacl [set-scope|set-priority|set-action|set-role] <ID> [parameters]"))
    def update_roleacl(self, args):
        """
        This method updates an existing ACL ROLE entry.

        (It can be accessed via parameter 'update roleacl')

        =========== =============
        key         description
        =========== =============
        args        The arguments-list we use as information basis
        =========== =============
        """

        action_type = self.get_value_from_args("roleacl-update-action", args)
        aid = self.get_value_from_args("id", args)

        try:
            if "set-scope" == action_type:
                scope = self.get_value_from_args("scope", args)
                self.resolver.updateACLRole('tmp_admin', aid, scope=scope)
                self.resolver.save_to_file()

            if "set-priority" == action_type:
                priority = self.get_value_from_args("priority", args)
                self.resolver.updateACLRole('tmp_admin', aid, priority=priority)
                self.resolver.save_to_file()

            if "set-action" == action_type:
                scope = self.get_value_from_args("scope", args)
                topic = self.get_value_from_args("topic", args)
                acls = self.get_value_from_args("acls", args)
                options = self.get_value_from_args("options", args)
                actions = [{'topic': topic, 'acls': acls, 'options': options}]
                self.resolver.updateACLRole('tmp_admin', aid, actions=actions, scope=scope)
                self.resolver.save_to_file()

            if "set-role" == action_type:
                rolename = self.get_value_from_args("rolename", args)
                self.resolver.updateACLRole('tmp_admin', aid, use_role=rolename)
                self.resolver.save_to_file()
        except ACLException as e:
            print e

    @helpDecorator(_("List all defined acls"))
    def list_acls(self, args):
        """
        This method lists all defined acls.

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
            print(_("   ... none"))
        for aclset in allSets:
            for acl in aclset:
                print("ID: %i \tSCOPE(%s)\tPRIORITY: %s \t BASE (%s)" % (acl.id, self.idToScopeStr(acl.scope), acl.priority, aclset.base))
                print("       \tMEMBER: %s" % (", ".join(acl.members)))
                if acl.uses_role:
                    print(_("\trefers to role: %s") % acl.role)
                else:
                    cnt = 1
                    print("     \tACTIONS:")
                    for action in acl.actions:
                        print("        - %s. %s (%s)  %s" % (cnt, action['topic'], action['acls'], action['options']))
                        cnt += 1

    @helpDecorator(_("List all defined roles"))
    def list_roles(self, args):
        """
        This method lists all defined acl roles.

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
            print("  Entries for role: %s" % aclrole)
            for acl in allRoles[aclrole]:
                print("ID: %i \tROLENAME: %s \t SCOPE (%s) \t PRIORITY (%s)" % (acl.id, allRoles[aclrole].name, self.idToScopeStr(acl.scope), str(acl.priority)))
                if acl.uses_role:
                    print(_("\trefers to role: %s") % acl.role)
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
    print(_(
        "\nAdministrate GOsa-ng permissions from the command line."
        "\n"
        "\nusage: acl-admin [-c CFGFILE] <list/add/update/remove> <acl/role> [parameters]"
        "\n"
        "\noptional arguments:"
        "\n  -c CFGFILE, --config CFGFILE"
        "\n    the agent-config file to use"
        "\n"))

    # Add methods marked with the helpDecorator
    mlist = sorted(helpDecorator.method_list)
    for method in mlist:
        sh = helpDecorator.method_list[method][0]
        lh = helpDecorator.method_list[method][1]
        method = re.sub("_", " ", method)
        if lh != "":
            print("  %s %s\n    %s\n" % (method.ljust(20), sh, lh))
        else:
            print("  %s %s" % (method.ljust(20), sh))


def main():

    # Print out help if no args is given.
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

        if (len(my_args) - 1) <= pos:
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
        print(_("Invalid argument list: %s") % (" ".join(my_args)))
        print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
