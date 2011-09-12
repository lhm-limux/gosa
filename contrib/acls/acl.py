import re
import json
import ldap


#TODO: Think about ldap relations, how to store and load objects.
#TODO: What about object groups, to be able to inlcude clients?
#TODO: Groups are not supported yet


"""
This is a collection of classes that can manager Access control lists.


AclSet
======
The base class of all ACL assignment is the 'AclSet' class which
combines a list of 'Acl' entries into a set of effective Acls.

The AclSet has a location property which specifies the location this set of
acls is valid for, e.g. dc=intranet,dc=gonicus,dc=de


Acl
===
The Acl class contains information about the acl definition, like
    |-> the scope
    |-> the users this acl is valid for
    |-> the actions described by
      |-> target    e.g. com.gonicus.objectFactory.Person.*
      |-> acls      e.g. rwxd
      |-> options   e.g. uid=hickert
    OR
      |-> role      The role to use instead of a direct acls


AclRole
=======
This class equals the 'AclSet' but in details it does not have a location, it
has just a name. This name can be used later in 'Acl' classes to reference to
this acl role.

And it cannot contain 'Acl' objects you've to use 'AclRoleEntry' objects.
AclRoleEntry objeects simply have no members.


AclRoleEntry
============
AclRoleEntries are used in 'AclRole' objects to combine several allowed
actions.


==========
AclResoler

The AclResolver is responsible for loading, saving and resolving permissions.


How an Acl assigment look could look like
=========================================

AclRole (test1)
 |-> AclRoleEntry
 |-> AclRoleEntry

AclSet
 |-> Acl
 |-> Acl
 |-> AclRole (test1)
 |-> Acl

"""


class AclSet(list):
    """
    This is a container for ACL entries.
    """
    location = None

    def __init__(self, location):
        self.location = location

    def get_location(self):
        """
        Returns the location for this AclSet.
        """
        return(self.location)

    def remove_acls_for_user(self, user):
        """
        Removes all permissions for the given user form this aclset.
        """
        for acl in self:
            if user in acl.members:
                acl.members.remove(user)

    def remove_acl(self, acl):
        """
        Removes an acl entry fromt this AclSet.
        """
        for cur_acl in self:
            if cur_acl == acl:
                self.remove(acl)
                return True
        return False

    def add(self, item):
        """
        Adds a new acl object to this aclSet.
        """
        if type(item) != Acl:
            raise TypeError('item is not of type %s' % Acl)

        if item.priority == None:
            item.priority = len(self)

        self.append(item)

        # Sort Acl items by id
        sorted(self, key=lambda item: item.priority)


class AclRole(list):
    """
    This is a container for ACL entries that should act like an acl role.
    """
    name = None
    priority = None

    def __init__(self, name):
        self.name = name

    def get_name(self):
        """
        Returns the name of the role.
        """
        return self.name

    def add(self, item):
        """
        Adds a new acl object to this aclSet.
        """
        if type(item) != AclRoleEntry:
            raise TypeError('item is not of type %s' % AclRoleEntry)

        if item.priority == None:
            item.priority = len(self)

        self.append(item)

        # Sort Acl items by id
        sorted(self, key=lambda item: item.priority)


class Acl(object):
    """
    The Acl class contains list of action for a set of members.
    These Acl classes can then be bundled and attached to a ldap base using
    the AclSet class.
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

    def __init__(self, scope=None, role=None):

        if scope == None:
            scope = Acl.SUB

        if scope not in (Acl.ONE, Acl.SUB, Acl.PSUB, Acl.RESET):
            raise(Exception("Invalid ACL type given"))

        self.scope = scope
        self.actions = []
        self.locations = []
        self.members = []

        if role:
            self.use_role(role)

    def use_role(self, role):
        """
        Mark this Acl to use a role instead of direkt permission settings.
        """
        self.uses_role = True
        self.role = role.name

    def add_member(self, member):
        """
        Adds a new member to this acl.
        """
        if type(member) != unicode:
            raise(Exception("Member should be of type str!"))
        self.members.append(member)

    def add_members(self, members):
        """
        Adds a list of new members to this acl.
        """
        if type(members) != list or len(members) == 0:
            print  members
            raise(Exception("Requires a list of members!"))

        for member in members:
            self.add_member(member)

    def add_action(self, target, acls, options):
        """
        Adds a new action to this acl.
        """
        if self.uses_role:
            raise Exception("Acl classes that use a role cannot define"
                   " additional costum acls!")

        acl = {
                'target': target,
                'acls': acls,
                'options': options}
        self.actions.append(acl)

    def get_members(self):
        """
        Returns the list of members this ACL is valid for.
        """
        return(self.member)

    def match(self, user, action, acls, options={}, skip_user_check=False):
        """
        Check of the requested user, action and the action options match this
        acl-object.
        """
        if user in self.members or skip_user_check:

            if self.uses_role:
                r = AclResolver.get_instance()
                print "ACL: Checking ACL role entries for role: '%s'!" % self.role
                for acl in r.acl_roles[self.role]:
                    if acl.match(user, action, acls, options, skip_user_check=True):
                        print "ACL:  ACL role entry matched!"
                        return True
            else:
                for act in self.actions:

                    # check for # and * placeholders
                    test_act = re.escape(act['target'])
                    test_act = re.sub(r'(^|\\.)(\\\*)(\\.|$)', '\\1.*\\3', test_act)
                    test_act = re.sub(r'(^|\\.)(\\#)(\\.|$)', '\\1[^\.]*\\3', test_act)

                    # Check if the requested-action matches the acl-action.
                    if not re.match(test_act, action):
                        continue

                    # Check if the required permissions are allowed.
                    if (set(acls) & set(act['acls'])) != set(acls):
                        continue

                    # Check if all required options are given
                    for entry in act['options']:

                        # Check for missing options
                        if entry not in options:
                            print "ACL:   Option '%s' is missing" % entry
                            continue

                        # Simply match string options.
                        if type(act['options'][entry]) == str and not re.match(act['options'][entry], options[entry]):
                            print "ACL:   Option '%s' with value '%s' does not match '%s'!" % (entry,
                                    act['options'][entry], options[entry])
                            continue

                        # Simply match string options.
                        elif act['options'][entry] != options[entry]:
                            print "ACL:   Option '%s' with value '%s' does not match '%s'!" % (entry,
                                    act['options'][entry], options[entry])
                            continue

                    # The acl rule matched!
                    return(True)

        # Nothing matched!
        return False

    def get_type(self):
        """
        Returns the type of an ACL.
        SUB, PSUB, RESET, ...
        """
        return(self.scope)


class AclRoleEntry(Acl):

    def __init__(self, scope=None, role=None):
        super(AclRoleEntry, self).__init__(scope=scope, role=role)

    def add_member(self, member):
        """
        Adds a new member to this acl.
        """
        raise Exception("Role Acls do not support direct members")


class AclResolver(object):
    instance = None
    acl_sets = None
    acl_roles = None

    def __init__(self):

        self.acl_sets = []
        self.acl_roles = {}

        # from config later on:
        self.base = "dc=gonicus,dc=de"
        self.acl_file = "agent.acl"

        self.load_from_file()

    def add_acl_set(self, acl):
        """
        Adds an AclSet object to the list of active-acl rules.
        """
        if not self.aclset_exists_by_location(acl.location):
            self.acl_sets.append(acl)
        else:
            raise Exception("An acl definition for location '%s' already exists!", acl.location)

    def add_acl_to_set(self, location, acl):
        """
        Add an acl rule to an existing acl set.
        """
        if not self.aclset_exists_by_location(location):
            raise Exception("No acl definition found for location '%s' cannot add acl!", location)
        else:
            aclset = self.get_aclset_by_location(location)
            aclset.add(acl)

        return(True)

    def add_acl_role(self, acl):
        """
        Adds an AclRole object to the list of active-acl roles.
        """
        self.acl_roles[acl.name] = acl

    def load_from_file(self):
        """
        Load acl definitions from a file
        """
        self.acl_sets = []

        acl_scope_map = {}
        acl_scope_map['one'] = Acl.ONE
        acl_scope_map['sub'] = Acl.SUB
        acl_scope_map['psub'] = Acl.PSUB
        acl_scope_map['reset'] = Acl.RESET

        try:
            data = json.loads(open(self.acl_file).read())

            # Add AclRoles
            roles = {}
            for name in data['roles']:
                roles[name] = AclRole(name)
                acls = data['roles'][name]
                for acl_entry in acls:
                    if 'role' in acl_entry:
                        role = roles[str(acl_entry['role'])]
                        acl = AclRoleEntry(role=role)
                    else:
                        acl = AclRoleEntry(acl_scope_map[acl_entry['scope']])
                        for action in acl_entry['actions']:
                            acl.add_action(action['target'], action['acls'], action['options'])

                    roles[name].add(acl)
                self.add_acl_role(roles[name])

            # Add AclSets
            for location in data['acl']:

                # The Acl defintion is based on an acl role.
                for acls_data in data['acl'][location]:

                    acls = AclSet(location)
                    for acl_entry in acls_data['acls']:

                        if 'role' in acl_entry:
                            acl_rule_set = self.acl_roles[acl_entry['role']]
                            acl = Acl(role=acl_rule_set)
                            acl.add_members(acl_entry['members'])
                            acls.add(acl)
                        else:
                            acl = Acl(acl_scope_map[acl_entry['scope']])
                            acl.add_members(acl_entry['members'])

                            for action in acl_entry['actions']:
                                acl.add_action(action['target'], action['acls'], action['options'])

                            acls.add(acl)
                    self.add_acl_set(acls)

        except IOError:
            return {}

    def save_to_file(self):
        """
        Save acl definition into a file
        """
        ret = {'acl': {}, 'roles':  {}}

        acl_scope_map = {}
        acl_scope_map[Acl.ONE] = 'one'
        acl_scope_map[Acl.SUB] = 'sub'
        acl_scope_map[Acl.PSUB] = 'psub'
        acl_scope_map[Acl.RESET] = 'reset'

        # Save AclSets
        for acl_set in self.acl_sets:

            # Prepare lists
            if acl_set.location not in ret['acl']:
                ret['acl'][acl_set.location] = []

            acls = []
            for acl in acl_set:
                if acl.uses_role:
                    entry = {'role': acl.role,
                            'members': acl.members}
                else:
                    entry = {'actions': acl.actions,
                            'members': acl.members,
                            'priority': acl.priority,
                            'scope': acl_scope_map[acl.scope]}
                acls.append(entry)
            ret['acl'][acl_set.location].append({'acls': acls})

        # Save AclRoles
        for role_name in self.acl_roles:
            ret['roles'][role_name] = []
            for acl in self.acl_roles[role_name]:
                if acl.uses_role:
                    entry = {'role': acl.role}
                else:
                    entry = {'actions': acl.actions,
                             'priority': acl.priority,
                             'scope': acl_scope_map[acl.scope]}
                ret['roles'][role_name].append(entry)

        # Store json data into a file
        with open(self.acl_file, 'w') as f:
            import json
            json.dump(ret, f, indent=2)

    def get_permissions(self, user, location, action, acls, options={}):
        """
        Check permissions for a given user and a location.
        """

        # Collect all acls matching the where statement
        allowed = False
        reset = False

        print "ACL: Checking acl for %s/%s/%s" % (user, location, str(action))

        # Remove the first part of the dn, until we reach the ldap base.
        while self.base in location:

            # Check acls for each acl set.
            for acl_set in self.acl_sets:

                # Skip acls that do not match the current ldap location.
                if location != acl_set.location:
                    continue

                # Check ACls
                for acl in acl_set:
                    if acl.match(user, action, acls, options):
                        print "ACL: Found matching acl in '%s'!" % location
                        if acl.get_type() == Acl.RESET:
                            print "ACL:  Acl reset for action '%s'!" % (action)
                            reset = True
                        elif acl.get_type() == Acl.PSUB:
                            print "ACL:  Found permanent acl for action '%s'!" % (action)
                            return True
                        elif acl.get_type() in (Acl.SUB, ) and not reset:
                            print "ACL:  Found acl for action '%s'!" % (action)
                            return True

            # Remove the first part of the dn
            location = ','.join(ldap.dn.explode_dn(location)[1::])

        return(allowed)

    @staticmethod
    def get_instance():
        if not AclResolver.instance:
            AclResolver.instance = AclResolver()

        return AclResolver.instance

    def list_acls(self):
        """
        Returns all AclSets attached to the resolver
        """
        return(self.acl_sets)

    def list_acl_locations(self):
        """
        Returns all locations wie acls attached to
        """
        loc = []
        for entry in self.acl_sets:
            loc.append(entry.location)
        return(loc)

    def list_role_names(self):
        return(self.acl_roles.keys())

    def list_roles(self):
        """
        Returns all AclRoles attached to the resolver
        """
        return(self.acl_roles)

    def is_role_used(self, role):

        for aclset in self.acl_sets:
            if self.__is_role_used(aclset, role):
                return(True)
        return(False)

    def __is_role_used(self, aclset, role):
        for acl in aclset:
            if acl.uses_role:
                if acl.role == role.name:
                    return(True)
                else:
                    role_acl_sets = self.acl_roles[acl.role]
                    if(self.__is_role_used(role_acl_sets, role)):
                        return(True)

        return(False)

    def get_aclset_by_location(self, location):
        """
        Returns an acl set by location.
        """
        if self.aclset_exists_by_location(location):
            for aclset in self.acl_sets:
                if aclset.location == location:
                    return aclset
        else:
            raise Exception("No acl definition found for location '%s'!" % (location,))

    def aclset_exists_by_location(self, location):
        """
        Checks if a AclSet for the given location exists or not.
        """
        for aclset in self.acl_sets:
            if aclset.location == location:
                return True
        return False

    def remove_aclset_by_location(self, location):
        """
        Removes a given acl rule.
        """
        if type(location) not in [str, unicode]:
            raise Exception("AclSets can only be removed by location name, '%s' is an invalid parameter" % location)

        # Remove all aclsets for the given location
        found = 0
        for aclset in self.acl_sets:
            if aclset.location == location:
                self.acl_sets.remove(aclset)
                found += 1

        # Send a message if there were no AclSets for the given location
        if  not found:
            raise Exception("No acl definitions for location '%s' were found, removal aborted!")

        pass

    def remove_role(self, name):
        """
        Removes an acl role.
        """

        # Allow to remove roles by passing AclRole-objects.
        if type(name) == AclRole:
            name = name.name

        # Check if we've got a valid name type.
        if type(name) not in [str, unicode]:
            raise Exception("Roles can only be removed by name, '%s' is an invalid parameter" % name)

        # Check if such a role-name exists and then try to remove it.
        if name in self.acl_roles:
            if self.is_role_used(self.acl_roles[name]):
                raise Exception("The role '%s' cannot be removed, it is still in use!" % name)
            else:
                del(self.acl_roles[name])
                return True
        else:
            raise Exception("No such role '%s', removal aborted!" % name)
        return False
