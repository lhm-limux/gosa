# -*- coding: utf-8 -*-
"""
This chapter details the way access control is handled within the GOsa core
engine.

How an ACL assigment could look like
------------------------------------

::

    ACLRole (test1)
     |-> ACLRoleEntry
     |-> ACLRoleEntry

    ACLSet
     |-> ACL
     |-> ACL
     |-> ACL -> ACLRole (test1)
     |-> ACL

--------
"""
import re
import os
import json
import ldap

from zope.interface import implements
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler
from gosa.common.components import Command

#TODO: Think about ldap relations, how to store and load objects.
#TODO: What about object groups, to be able to inlcude clients?
#TODO: Groups are not supported yet
#TODO: Allow Wildcards in ACL-Options
#TODO: Add set_members method to ACLs.


class ACLException(Exception):
    pass


class ACLSet(list):
    """
    The base class of all ACL assignments is the 'ACLSet' class which
    combines a list of ``ACL`` entries into a set of effective ACLs.

    The ACLSet has a location property which specifies the location, this set of
    acls, is valid for. E.g. dc=example,dc=net

    ============== =============
    Key            Description
    ============== =============
    location       The location this ACLSet is created for.
    ============== =============

    >>> # Create an ACLSet for location 'dc=example,dc=net'
    >>> # (if you do not pass the location, the default of your ldap setup will be used)
    >>> aclset = ACLSet('dc=example,dc=net')
    >>> resolver = ACLResolver()
    >>> resolver.add_acl_set(aclset)
    """
    location = None

    def __init__(self, location=None):
        super(ACLSet, self).__init__()

        # If no location is given use the default one.
        if not location:
            location = LDAPHandler.get_instance().get_base()

        self.location = location

    def get_location(self):
        """
        Returns the location for this ACLSet.
        """
        return(self.location)

    def remove_acls_for_user(self, user):
        """
        Removes all permission for the given user form this ACLSet.

        ============== =============
        Key            Description
        ============== =============
        user           The username to remove acls for.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)
            acl.add_members([u'tester1', u'tester2'])
            acl.add_action('com.#.factory', 'rwx')
            acl.set_priority(100)
            aclset.add(acl)

            aclset.remove_acls_for_user('tester1')

            ...

        """
        for acl in self:
            if user in acl.members:
                acl.members.remove(user)

    def remove_acl(self, acl):
        """
        Removes an acl entry fromt this ACLSet.

        ============== =============
        Key            Description
        ============== =============
        acl            The ACL object to remove.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)
            acl.add_members([u'tester1', u'tester2'])
            acl.add_action('com.#.factory', 'rwx')
            acl.set_priority(100)
            aclset.add(acl)

            aclset.remove_acl(acl)

        """
        for cur_acl in self:
            if cur_acl == acl:
                self.remove(acl)
                return True
        return False

    def add(self, item):
        """
        Adds a new ``ACL`` object to this ``ACLSet``.

        ============== =============
        Key            Description
        ============== =============
        acl            The ACL object to add.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)
            acl.add_members([u'tester1', u'tester2'])
            acl.add_action('com.#.factory', 'rwx')
            acl.set_priority(100)

            aclset.add(acl)

        """
        if type(item) != ACL:
            raise TypeError('item is not of type %s' % ACL)

        if item.priority == None:
            item.priority = len(self)

        self.append(item)

        # Sort Acl items by id
        self.sort(key=lambda item: (item.priority * 1))

    def __str__(self):
        return(self.repr_self())

    def repr_self(self, indent=0):
        """
        Create a human readable reprentation of this ACLSet object.
        """

        # Only draw to a maximum level of 20 sub entries
        if indent > 20:
            return " " * indent + "...\n"

        # Build a human readable representation of this aclset and its children.
        rstr = "%s<ACLSet: %s>" % (" " * indent, self.location)
        for entry in self:
            rstr += entry.repr_self(indent + 1)

        return rstr


class ACLRole(list):
    """
    This is a container for ``ACLRoleEntries`` entries that should act like a role.
    An ``ACLRole`` has a name which can be used in ``ACL`` objects to use the role.

    ============== =============
    Key            Description
    ============== =============
    name           The name of the role we want to create.
    ============== =============

    This class equals the ``ACLSet`` class, but in details it does not have a location, instead
    it has name. This name can be used later in 'ACL' classes to refer to
    this acl role.

    And instead of ``ACL-objects`` it uses ``ACLRoleEntry-objects`` to assemble
    a set of acls::

        >>> # Create an ACLRole object
        >>> aclrole = ACLRole('role1')
        >>> acl = ACLRoleEntry(scope=ACL.SUB)
        >>> acl.add_action(...)
        >>> aclrole.add(acl)

        >>> # Now add the role to the resolver
        >>> resolver = ACLResolver()
        >>> resolver.add_acl_set(aclrole)

        >>> # You can use this role like this in ACL entries of an ACLset:
        >>> aclset = ACLSet()
        >>> acl = ACL(role=aclrole)
        >>> aclset.add(acl)
        >>> resolver.add_acl_set(aclset)

    Or you can use this role within another role like this::

        >>> # Create an ACLRole object
        >>> aclrole1 = ACLRole('role1')
        >>> acl = ACLRoleEntry(scope=ACL.SUB)
        >>> acl.add_action(...)
        >>> aclrole1.add(acl)

        >>> # Now add the role to the resolver
        >>> resolver = ACLResolver()
        >>> resolver.add_acl_set(aclrole1)

        >>> # Create antoher role which refers to role1
        >>> aclrole2 = ACLRole('role2')
        >>> acl = ACLRoleEntry(role=role1)
        >>> aclrole2.add(acl)
        >>> resolver = ACLResolver()
        >>> resolver.add_acl_set(aclrole2)

        >>> # Now use the role2 in an ACL defintion. (Role2 point to Role1 now.)
        >>> aclset = ACLSet()
        >>> acl = ACL(role=aclrole2)
        >>> aclset.add(acl)
        >>> resolver.add_acl_set(aclset)
    """
    name = None
    priority = None

    def __init__(self, name):
        super(ACLRole, self).__init__()
        self.name = name

    def add(self, item):
        """
        Add a new ``ACLRoleEntry`` object to this ``ACLRole``.

        ============== =============
        Key            Description
        ============== =============
        item           The ``ACLRoleEntry`` item to add to this role.
        ============== =============

        Example::

            # Create an ACLRole
            role = ACLRole('role1')
            acl = ACLRoleEntry(scope=ACL.ONE)
            acl.add_action('com.gosa.factory', 'rwx')

            role.add(acl)

        """
        if type(item) != ACLRoleEntry:
            raise TypeError('item is not of type %s' % ACLRoleEntry)

        # Create an item priority if it does not exists.
        if item.priority == None:
            item.priority = len(self)

        self.append(item)

        # Sort Acl items by id
        self.sort(key=lambda item: (item.priority * -1))

    def get_name(self):
        """
        Returns the name of the role.
        """
        return self.name

    def __str__(self):
        return(self.repr_self())

    def repr_self(self, indent=0):
        """
        Create a human readable reprentation of this ACLRole object.
        """

        # Only draw to a maximum level of 20 sub entries
        if indent > 20:
            return " " * indent + "...\n"

        # Build a human readable representation of this role and its children.
        rstr = "%s<ACLRole: %s>" % (" " * indent, self.name)
        for entry in self:
            rstr += entry.repr_self(indent + 1)

        return rstr


class ACL(object):
    """
    The ``ACL`` object describes a set of actions that can be accessed in a given scope.
    ``ACL`` classes can then be bundled in ``ACLSet`` objects and attached to locations.

    ============== =============
    Key            Description
    ============== =============
    scope          The scope this acl is valid for.
    role           You can either define permission actions directly or you can use an ``ACLRole`` instead
    ============== =============

    Valid scope values:

        * ``ACL.ONE`` for one level.
        * ``ACL.SUB`` for all sub-level. This can be revoked using ``ACL.RESET``
        * ``ACL.RESET`` revokes the actions described in this ``ACL`` object for all sub-levels of the tree.
        * ``ACL.PSUB`` for all sub-level, cannot be revoked using ``ACL.RESET``

    The ACL class contains list of actions for a set of members.
    These ACL classes can then be bundled and attached to a location base using
    the ``ACLSet`` class.

    ======== ================
    Type     Description
    ======== ================
    Scope    The scope specifies where the ACL is valid for, e.g. ONE-level, all SUB-levels or RESET previous ACLs
    Members  A list of users this acl is valid for.
    Role     Instead of actions you can also refer to a ACLRole object.
    Actions  You can have multiple actions, where one action is described by ``a target``, a ``set of acls`` and additional ``options`` that have to be checked while ACLs are resolved.
    ======== ================

        >>> # Create an ACLSet object
        >>> aclset = ACLSet()

        >>> # Create an ACL object and attach it to the ACLSet
        >>> acl = ACL()
        >>> acl.set_priority(0)
        >>> acl.set_members([u"user1", u"user2"])
        >>> acl.add_action('org.gosa.factory.Person.cn','rwx')
        >>> aclset.add(acl)

        >>> # Now add the set to the resolver
        >>> resolver = ACLResolver()
        >>> resolver.add_acl_set(aclset)

        >>> # You can now check for acls, both should return True now.
        >>> resolver.check('user1', 'org.gosa.factory.Person.cn', 'r')
        >>> resolver.check('user1', 'org.gosa.factory.Person.cn', 'rwx')

    ACL members can also contain regular expressions, like this:

        >>> acl.set_members([u"user1", u"^user[0-9]*$"])
        >>> ...
        >>> resolver.check('user45', 'org.gosa.factory.Person.cn', 'r')

    Also action can have wildcards, but only two right now:

        >>> acl.add_action('org.gosa.#.Person.cn','rwx')
        >>> acl.add_action('org.gosa.*.Person.cn','rwx')

    Where ``#`` allow to ignore one level on the target action and ``*`` allows to ignore one or more levels:

    ``com.#.factory`` would match with ``com.test.factory`` or ``com.something.factory``

    ``com.*.factory`` would match with ``com.test.factory``, ``com.something.factory`` or ``com.level1.level2.level3.factory``
    """
    priority = None

    ONE = 1
    SUB = 2
    PSUB = 3
    RESET = 4

    members = None
    actions = None
    scope = None
    uses_role = False
    role = None

    def __init__(self, scope=SUB, role=None):
        self.env = Environment.getInstance()

        self.actions = []
        self.members = []

        # Is this a role base or manually configured ACL object.
        if role:
            self.__use_role(role)
        else:

            if scope not in (ACL.ONE, ACL.SUB, ACL.PSUB, ACL.RESET):
                raise(Exception("Invalid ACL type given"))

            self.scope = scope

    def __use_role(self, rolename):
        """
        Mark this ACL to use a role instead of direkt permission settings.

        ============== =============
        Key            Description
        ============== =============
        rolename       The name of the role to use.
        ============== =============

        """
        if type(rolename) not in [str, unicode]:
            raise ACLException("Expected type str or unicode for rolename!")

        r = ACLResolver.instance
        if rolename in r.acl_roles:
            self.uses_role = True
            self.role = rolename
        else:
            raise ACLException("Unknown role '%s'!" % rolename)

    def set_priority(self, priority):
        """
        Sets the priority of this ACL object. Lower values mean higher priority.

        If no priority is given, a priority of 0 will be used when this ACL gets added to an ACLSet, the next will get 1, then 2 aso.

        ============== =============
        Key            Description
        ============== =============
        priority       The new priority value for this ACl.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)
            acl.add_members([u'tester1', u'tester2'])
            acl.add_action('com.#.factory', 'rwx')

            acl.set_priority(100)

        """
        self.priority = priority

    def add_member(self, member):
        """
        Adds a new member to this acl.

        ============== =============
        Key            Description
        ============== =============
        member         A username that have to be added.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)

            acl.add_member(u'peter')

        """
        if type(member) != unicode:
            raise(ACLException("Member should be of type str!"))
        self.members.append(member)

    def add_members(self, members):
        """
        Adds a list of new members to this acl.

        ============== =============
        Key            Description
        ============== =============
        members        A list of usernames that have to be added.
        ============== =============

        Example::

            aclset = ACLSet()
            acl = ACL(scope=ACL.ONE)

            acl.add_members([u'peter', u'klaus'])

        """
        if type(members) != list:
            raise(ACLException("Requires a list of members!"))

        for member in members:
            self.add_member(member)

    def add_action(self, target, acls, options=None):
        """
        Adds a new action to this ACL object.

        ============== =============
        Key            Description
        ============== =============
        target         The target action we want to create ACLs for. E.g. 'com.gosa.factory.Person'
        acls           The acls this action contain. E.g. 'rwcdm'.
        options        Special additional options that have to be checked.
        ============== =============

        **Targets**

        Targets can contain placeholder to be more flexible when it come to resolving acls.
        You can use ``#`` and ``*`` where ``#`` matches for one level and ``*`` for multiple target levels.

        For example ``gosa.#.factory`` would match for:
         * gosa.test.factory
         * gosa.hallo.factory
        but not for:
         * gosa.factory
         * gosa.level1.level2.factory

        Where ``gosa.*.factory`` matches for:
         * gosa.factory
         * gosa.level1.factory
         * gosa.level1.level2.factory

        **Acls**

        The acls paramter describes the action we can perform on a given ``target``.
        Possible actions are:

         * r - Read
         * w - Write
         * m - Move
         * c - Create
         * d - Delete
         * s - Search - or beeing found
         * x - Execute
         * e - Receive event

        The actions have to passed as a string, which contains all actions at once::
            >>> add_action(``target``, "rwcdm", ``options``)

        **Options**

        Options are additional check parameters that have to be fullfilled to get this acl to match.

        The ``options`` parameter is a dictionary which contains a key and a value for each additional option we want to check for, e.g. ::
            >>> add_action(``target``, ``acls``, {'uid': 'hanspeter', 'ou': 'technik'})

        If you've got a user object as dictionary, then you can check permissions like this::
            >>> resolver.check('some.target', 'rwcdm', user1)

        The resolver will then check if the keys ``uid`` and ``ou`` are present in the user1 dictionary and then check if the values match.
        If not all options match, the ACL will not match.

        """
        if self.uses_role:
            raise ACLException("ACL classes that use a role cannot define"
                   " additional costum acls!")

        acl = {
                'target': target,
                'acls': acls,
                'options': options if options else {}}
        self.actions.append(acl)

    def get_members(self):
        """
        Returns the list of members this ACL is valid for.
        """
        return(self.members)

    def __str__(self):
        return(self.repr_self())

    def repr_self(self, indent=0):
        """
        Generates a human readable representation of the ACL-object.
        """
        if self.uses_role:
            r = ACLResolver.instance
            rstr = "\n%s<ACL> %s" % (" " * indent, str(self.members))
            rstr += "\n%s" % r.acl_roles[self.role].repr_self(indent + 1)
        else:
            rstr = "\n%s<ACL scope(%s)> %s: " % ((" " * indent), self.scope, str(self.members))
            for entry in self.actions:
                rstr += "\n%s%s:%s %s" % ((" " * (indent + 1)), entry['target'], str(entry['acls']), str(entry['options']))
        return rstr

    def match2(self, user, target, acls, options=None, skip_user_check=False, used_roles=None):
        """
        Check if this ``ACL`` object matches the given criteria.

        .. warning::
            Do NOT use this to validate permissions. Use  ACLResolver->check() instead

        =============== =============
        Key             Description
        =============== =============
        user            The user we want to check for. E.g. 'hans'
        target          The target action we want to check for. E.g. 'com.gosa.factory'
        acls            A string containing the acls we want to check for.
        options         Special additional options that have to be checked.
        skip_user_check Skips checks for users, this is required to resolve roles.
        used_roles      A list of roles used in this recursion, to be able to check for endless-recursions.
        =============== =============
        """

        # Initialize list of already used roles, to avoid recursions
        if not used_roles:
            used_roles = []

        # Check if the given user string matches one of the defined users
        if skip_user_check:
            user_match = True
        else:
            user_match = False
            for suser in self.members:
                if re.match(suser, user):
                    user_match = True
                    break

        if user_match:

            if self.uses_role:

                # Check for recursions while resolving the acls.
                if self.role in used_roles:
                    raise ACLException("Recursion in acl resolution, loop in role '%s'! Included roles %s." % (self.role, str(used_roles)))

                # Resolve acls used in the role.
                used_roles.append(self.role)
                r = ACLResolver.instance
                self.env.log.debug("checking ACL role entries for role: %s" % self.role)
                for acl in r.acl_roles[self.role]:
                    (match, scope) = acl.match2(user, target, acls, options if options else {}, True, used_roles)
                    if match:
                        self.env.log.debug("ACL role entry matched for role '%s'" % self.role)
                        return (match, scope)
            else:
                for act in self.actions:

                    # check for # and * placeholders
                    test_act = re.escape(act['target'])
                    test_act = re.sub(r'(^|\\.)(\\\*)(\\.|$)', '\\1.*\\3', test_act)
                    test_act = re.sub(r'(^|\\.)(\\#)(\\.|$)', '\\1[^\.]*\\3', test_act)

                    # Check if the requested-action matches the acl-action.
                    if not re.match(test_act, target):
                        continue

                    # Check if the required permission are allowed.
                    if (set(acls) & set(act['acls'])) != set(acls):
                        continue

                    # Check if all required options are given
                    for entry in act['options']:

                        # Check for missing options
                        if entry not in options:
                            self.env.log.debug("ACL option '%s' is missing" % entry)
                            continue

                        # Simply match string options.
                        if type(act['options'][entry]) == str and not re.match2(act['options'][entry], options[entry]):
                            self.env.log.debug("ACL option '%s' with value '%s' does not match with '%s'" % (entry,
                                        act['options'][entry], options[entry]))
                            continue

                        # Simply match string options.
                        elif act['options'][entry] != options[entry]:
                            self.env.log.debug("ACL option '%s' with value '%s' does not match with '%s'" % (entry,
                                        act['options'][entry], options[entry]))
                            continue

                    # The acl rule matched!
                    return (True, self.scope)

        # Nothing matched!
        return (False, None)

    def match(self, user, target, acls, options=None, skip_user_check=False, used_roles=None):
        """
        Check if this ``ACL`` object matches the given criteria.

        .. warning::
            Do NOT use this to validate permissions. Use  ACLResolver->check() instead

        =============== =============
        Key             Description
        =============== =============
        user            The user we want to check for. E.g. 'hans'
        target          The target action we want to check for. E.g. 'com.gosa.factory'
        acls            A string containing the acls we want to check for.
        options         Special additional options that have to be checked.
        skip_user_check Skips checks for users, this is required to resolve roles.
        used_roles      A list of roles used in this recursion, to be able to check for endless-recursions.
        =============== =============
        """

        # Initialize list of already used roles, to avoid recursions
        if not used_roles:
            used_roles = []

        # Check if the given user string matches one of the defined users
        if skip_user_check:
            user_match = True
        else:
            user_match = False
            for suser in self.members:
                if re.match(suser, user):
                    user_match = True
                    break

        if user_match:

            if self.uses_role:

                # Check for recursions while resolving the acls.
                if self.role in used_roles:
                    raise ACLException("Recursion in acl resolution, loop in role '%s'! Included roles %s." % (self.role, str(used_roles)))

                # Resolve acls used in the role.
                used_roles.append(self.role)
                r = ACLResolver.instance
                self.env.log.debug("checking ACL role entries for role: %s" % self.role)
                for acl in r.acl_roles[self.role]:
                    if acl.match(user, target, acls, options if options else {}, True, used_roles):
                        self.env.log.debug("ACL role entry matched for role '%s'" % self.role)
                        return True
            else:
                for act in self.actions:

                    # check for # and * placeholders
                    test_act = re.escape(act['target'])
                    test_act = re.sub(r'(^|\\.)(\\\*)(\\.|$)', '\\1.*\\3', test_act)
                    test_act = re.sub(r'(^|\\.)(\\#)(\\.|$)', '\\1[^\.]*\\3', test_act)

                    # Check if the requested-action matches the acl-action.
                    if not re.match(test_act, target):
                        continue

                    # Check if the required permission are allowed.
                    if (set(acls) & set(act['acls'])) != set(acls):
                        continue

                    # Check if all required options are given
                    for entry in act['options']:

                        # Check for missing options
                        if entry not in options:
                            self.env.log.debug("ACL option '%s' is missing" % entry)
                            continue

                        # Simply match string options.
                        if type(act['options'][entry]) == str and not re.match(act['options'][entry], options[entry]):
                            self.env.log.debug("ACL option '%s' with value '%s' does not match with '%s'" % (entry,
                                        act['options'][entry], options[entry]))
                            continue

                        # Simply match string options.
                        elif act['options'][entry] != options[entry]:
                            self.env.log.debug("ACL option '%s' with value '%s' does not match with '%s'" % (entry,
                                        act['options'][entry], options[entry]))
                            continue

                    # The acl rule matched!
                    return(True)

        # Nothing matched!
        return False

    def get_scope(self):
        """
        Returns the scope of an ACL.
        SUB, PSUB, RESET, ...
        """
        return(self.scope)


class ACLRoleEntry(ACL):
    """
    The ``ACLRoleEntry`` object describes a set of action that can be accessed in a given scope.
    ``ACLRoleEntry`` classes can then be bundled in ``ACLRole`` objects, to build up roles.

    ============== =============
    Key            Description
    ============== =============
    scope          The scope this acl is valid for.
    role           You can either define permission action directly or you can use an ``ACLRole`` instead
    ============== =============

    Valid scope values:

        * ``ACL.ONE`` for one level.
        * ``ACL.SUB`` for all sub-level. This can be revoked using ``ACL.RESET``
        * ``ACL.RESET`` revokes the actions described in this ``ACL`` object for all sub-levels of the tree.
        * ``ACL.PSUB`` for all sub-level, cannot be revoked using ``ACL.RESET``

    Members properties:

    ======== ================
    Type     Description
    ======== ================
    Scope    The scope specifies where the ACL is valid for, e.g. ONE-level, all SUB-levels or RESET previous ACLs
    Role     Instead of actions you can also refer to a ACLRole object.
    Actions  You can have multiple actions, where one action is described by ``a target``, a ``set of acls`` and additional ``options`` that have to be checked while ACLs are resolved.
    ======== ================
    """

    def __init__(self, scope=ACL.SUB, role=None):
        super(ACLRoleEntry, self).__init__(scope=scope, role=role)

    def add_member(self, member):
        """
        An overloaded method from ACL which disallows to add users.
        """
        raise ACLException("Role ACLs do not support direct members")


class ACLResolver(object):
    """
    The ACLResolver is responsible for loading, saving and resolving
    permission::

        >>> resolver = ACLResolver()
        >>> self.resolver.check('user1','org.gosa.factory','r')
        >>> self.resolver.check('user1','org.gosa.factory','rwx', 'dc=example,dc=net')

    If no location is given (last parameter of check), the default location will be used. (The default location is the configured LDAP base).

    To list all defined roles and acls you can use::

        >>> resolver = ACLResolver()
        >>> resolver.list_roles()
        >>> resolver.list_acls()

    To print a human readable output of an ACLSet just use the string
    repesentation::

        >>> acls = ACLSet('...')
        >>> acl = ACL(scope=ACL.ONE)
        >>> acls.add(acl)
        >>> acls
    """
    implements(IInterfaceHandler)
    instance = None
    acl_sets = None
    acl_roles = None
    admins = []

    _priority_ = 0

    def __init__(self):
        self.env = Environment.getInstance()
        self.env.log.debug("initializing ACL resolver")

        # Load override admins from configuration
        admins = self.env.config.get("core.admins", default=None)
        if admins:
            admins = re.sub(r'\s', '', admins)
            self.env.log.info("adding users to the ACL override: %s" % admins)
            self.admins = admins.split(",")

        # Load default LDAP base
        lh = LDAPHandler.get_instance()
        self.base = lh.get_base()
        self.acl_file = os.path.join(self.env.config.getBaseDir(), "agent.acl")

        # Load initial ACL information from file
        self.clear()
        self.load_from_file()
        ACLResolver.instance = self

    def clear(self):
        """
        Clears all information abouts roles and acls.
        This is called during initialization of the ACLResolver class.
        """

        self.acl_sets = []
        self.acl_roles = {}

    def add_acl_set(self, acl):
        """
        Adds an ACLSet object to the list of active-acl rules.
        """
        if not self.aclset_exists_by_location(acl.location):
            self.acl_sets.append(acl)
        else:
            raise ACLException("An acl definition for location '%s' already exists!", acl.location)

    def add_acl_to_set(self, location, acl):
        """
        Adds an ACL-object to an existing ACLSet.

        ============== =============
        Key            Description
        ============== =============
        location       The location we want to add an ACL object to.
        acl            The ACL object we want to add.
        ============== =============
        """
        if not self.aclset_exists_by_location(location):
            raise ACLException("No acl definition found for location '%s' cannot add acl!", location)
        else:
            aclset = self.get_aclset_by_location(location)
            aclset.add(acl)

        return(True)

    def add_acl_role(self, role):
        """
        Adds a new ACLRole-object to the ACLResolver class.

        ============== =============
        Key            Description
        ============== =============
        role           The ACLRole object we want to add.
        ============== =============
        """
        self.acl_roles[role.name] = role

    def load_from_file(self):
        """
        Load the acl definitions from the configured storage file.
        """
        self.clear()
        self.acl_sets = []

        acl_scope_map = {}
        acl_scope_map['one'] = ACL.ONE
        acl_scope_map['sub'] = ACL.SUB
        acl_scope_map['psub'] = ACL.PSUB
        acl_scope_map['reset'] = ACL.RESET

        try:
            data = json.loads(open(self.acl_file).read())

            # Add ACLRoles
            roles = {}
            unresolved = []
            for name in data['roles']:

                # Create a new role object on demand.
                if name not in roles:
                    roles[name] = ACLRole(name)

                # Check if this role was referenced before but not initialized
                if name in unresolved:
                    unresolved.remove(name)

                # Append the role acls to the ACLRole object
                acls = data['roles'][name]
                for acl_entry in acls:

                    # The acl entry refers to another role ebtry.
                    if 'role' in acl_entry:

                        # If the role was'nt loaded yet, the create and attach requested role
                        #  to the list of roles, but mark it as unresolved
                        rn = str(acl_entry['role'])
                        if rn not in roles:
                            unresolved.append(rn)
                            roles[rn] = ACLRole(rn)
                            self.add_acl_role(roles[rn])

                        # Add the acl entry entry which refers to the role.
                        acl = ACLRoleEntry(role=roles[rn])
                        acl.use_role(roles[rn])
                        acl.set_priority(acl_entry['priority'])
                        roles[name].add(acl)
                        self.add_acl_role(roles[name])
                    else:

                        # Add a normal (non-role) base acl entry
                        acl = ACLRoleEntry(acl_scope_map[acl_entry['scope']])
                        for action in acl_entry['actions']:
                            acl.add_action(action['target'], action['acls'], action['options'])
                        roles[name].add(acl)

            # Check if we've got unresolved roles!
            if len(unresolved):
                raise ACLException("Loading ACls failed, we've got unresolved roles references: '%s'!" % (str(unresolved), ))

            # Add the recently created roles.
            for role_name in roles:
                self.add_acl_role(roles[role_name])

            # Add ACLSets
            for location in data['acl']:

                # The ACL defintion is based on an acl role.
                for acls_data in data['acl'][location]:

                    acls = ACLSet(location)
                    for acl_entry in acls_data['acls']:

                        if 'role' in acl_entry:
                            acl_rule_set = self.acl_roles[acl_entry['role']]
                            acl = ACL(role=acl_rule_set)
                            acl.add_members(acl_entry['members'])
                            acl.set_priority(acl_entry['priority'])
                            acls.add(acl)
                        else:
                            acl = ACL(acl_scope_map[acl_entry['scope']])
                            acl.add_members(acl_entry['members'])
                            acl.set_priority(acl_entry['priority'])

                            for action in acl_entry['actions']:
                                acl.add_action(action['target'], action['acls'], action['options'])

                            acls.add(acl)
                    self.add_acl_set(acls)

        except IOError:
            return {}

    def save_to_file(self):
        """
        Saves the acl definitions back the configured storage file.
        """
        ret = {'acl': {}, 'roles':  {}}

        acl_scope_map = {}
        acl_scope_map[ACL.ONE] = 'one'
        acl_scope_map[ACL.SUB] = 'sub'
        acl_scope_map[ACL.PSUB] = 'psub'
        acl_scope_map[ACL.RESET] = 'reset'

        # Save ACLSets
        for acl_set in self.acl_sets:

            # Prepare lists
            if acl_set.location not in ret['acl']:
                ret['acl'][acl_set.location] = []

            acls = []
            for acl in acl_set:
                if acl.uses_role:
                    entry = {'priority': acl.priority,
                            'role': acl.role,
                            'members': acl.members}
                else:
                    entry = {'actions': acl.actions,
                            'members': acl.members,
                            'priority': acl.priority,
                            'scope': acl_scope_map[acl.scope]}
                acls.append(entry)
            ret['acl'][acl_set.location].append({'acls': acls})

        # Save ACLRoles
        for role_name in self.acl_roles:
            ret['roles'][role_name] = []
            for acl in self.acl_roles[role_name]:
                if acl.uses_role:
                    entry = {'role': acl.role,
                             'priority': acl.priority}
                else:
                    entry = {'actions': acl.actions,
                             'priority': acl.priority,
                             'scope': acl_scope_map[acl.scope]}
                ret['roles'][role_name].append(entry)

        # Store json data into a file
        with open(self.acl_file, 'w') as f:
            json.dump(ret, f, indent=2)

    def check(self, user, target, acls, options=None, location=None):
        """
        Check permission for a given user and a location.

        ============== =============
        Key            Description
        ============== =============
        user           The user we want to check for.
        target         The target string, e.g. 'com.gosa.factory'
        acls           The list of acls, we want to check for, e.g. 'rcwdm'
        options        A dictionary containing extra options to check for.
        location       The location we want to check acls in.
        ============== =============

        Take a look at ACL.add_action for details about ``target``, ``options`` and ``acls``.

        Example::
            >>> resolver = ACLResolver()
            >>> self.resolver.check('user1','org.gosa.factory','r')
            >>> self.resolver.check('user1','org.gosa.factory','rwx', 'dc=example,dc=net')

        """

        # Admin users are allowed to do anything.
        if user in self.admins:
            return True

        # Load default location if needed
        if not location:
            location = self.base

        # Collect all acls matching the where statement
        allowed = False
        reset = False

        self.env.log.debug("checking ACL for %s/%s/%s" % (user, location,
            str(target)))

        # Remove the first part of the dn, until we reach the ldap base.
        orig_loc = location
        while self.base in location:

            # Check acls for each acl set.
            for acl_set in self.acl_sets:

                # Skip acls that do not match the current ldap location.
                if location != acl_set.location:
                    continue

                # Check ACls
                for acl in acl_set:

                    (match, scope) = acl.match2(user, target, acls, options)
                    if match:

                        self.env.log.debug("found matching ACL in '%s'" % location)
                        if scope == ACL.RESET:
                            self.env.log.debug("found ACL reset for target '%s'" % target)
                            reset = True
                        else:

                            if scope == ACL.PSUB:
                                self.env.log.debug("found permanent ACL for target '%s'" % target)
                                return True

                            elif (scope == ACL.SUB):
                                if not reset:
                                    self.env.log.debug("found ACL for target '%s' (SUB)" % target)
                                    return True
                                else:
                                    self.env.log.debug("ACL DO NOT match due to reset. (SUB)")

                            elif (scope == ACL.ONE and orig_loc == acl_set.location):
                                if not reset:
                                    self.env.log.debug("found ACL for target '%s' (ONE)" % target)
                                    return True
                                else:
                                    self.env.log.debug("ACL DO NOT match due to reset. (ONE)")

            # Remove the first part of the dn
            location = ','.join(ldap.dn.explode_dn(location)[1::])

        return(allowed)

    def list_acls(self):
        """
        Returns all ACLSets attached to the resolver
        """
        return(self.acl_sets)

    def list_acl_locations(self):
        """
        Returns all locations wie acls attached to
        """
        return map(lambda entry: entry.location, self.acl_sets)

    def list_role_names(self):
        return(self.acl_roles.keys())

    def list_roles(self):
        """
        Returns all ACLRoles attached to the resolver
        """
        return(self.acl_roles)

    def is_role_used(self, rolename):
        """
        Checks whether the given ACLRole object is used or not.

        ============== =============
        Key            Description
        ============== =============
        rolename       The name of the role we want to check for.
        ============== =============
        """

        for aclset in self.acl_sets:
            if self.__is_role_used(aclset, rolename):
                return(True)
        return(False)

    def __is_role_used(self, aclset, rolename):
        for acl in aclset:
            if acl.uses_role:
                if acl.role == rolename:
                    return(True)
                else:
                    role_acl_sets = self.acl_roles[acl.role]
                    if(self.__is_role_used(role_acl_sets, rolename)):
                        return(True)

        return(False)

    def get_aclset_by_location(self, location):
        """
        Returns an acl set by location.

        ============== =============
        Key            Description
        ============== =============
        location       The location we want to return the ACLSets for.
        ============== =============
        """
        if self.aclset_exists_by_location(location):
            for aclset in self.acl_sets:
                if aclset.location == location:
                    return aclset
        else:
            raise ACLException("No acl definition found for location '%s'!" % (location,))

    def aclset_exists_by_location(self, location):
        """
        Checks if a ACLSet for the given location exists or not.

        ============== =============
        Key            Description
        ============== =============
        location       The location we want to check for.
        ============== =============
        """
        for aclset in self.acl_sets:
            if aclset.location == location:
                return True
        return False

    def remove_aclset_by_location(self, location):
        """
        Removes a given ACLSet by location.

        ============== =============
        Key            Description
        ============== =============
        location       The location we want to delete ACLSets for.
        ============== =============
        """
        if type(location) not in [str, unicode]:
            raise ACLException("ACLSets can only be removed by location name, '%s' is an invalid parameter" % location)

        # Remove all aclsets for the given location
        found = 0
        for aclset in self.acl_sets:
            if aclset.location == location:
                self.acl_sets.remove(aclset)
                found += 1

        # Send a message if there were no ACLSets for the given location
        if  not found:
            raise ACLException("No acl definitions for location '%s' were found, removal aborted!")

    def remove_role(self, name):
        """
        Removes an acl role by name.

        ============== =============
        Key            Description
        ============== =============
        name           The name of the role that have to be removed.
        ============== =============
        """

        # Allow to remove roles by passing ACLRole-objects.
        if type(name) == ACLRole:
            name = name.name

        # Check if we've got a valid name type.
        if type(name) not in [str, unicode]:
            raise ACLException("Roles can only be removed by name, '%s' is an invalid parameter" % name)

        # Check if such a role-name exists and then try to remove it.
        if name in self.acl_roles:
            if self.is_role_used(self.acl_roles[name]):
                raise ACLException("The role '%s' cannot be removed, it is still in use!" % name)
            else:
                del(self.acl_roles[name])
                return True
        else:
            raise ACLException("No such role '%s', removal aborted!" % name)
        return False
