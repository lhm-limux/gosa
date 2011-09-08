import re
import json
import ldap


#TODO: Think about ldap relations, how to store and load objects.
#TODO: What about object groups, to be able to inlcude clients?
#TODO: Groups are not supported yet


"""
This is a collection of classes that can manager Access control lists.

AclSet      - Is a container class for Acl objects. An AclSet-object can be attached
              to ldap organizationalUnits to restrict permissions for a set of
              users.
Acl         - This class represents a single ACL rule, Acl-objects can be
              bundled in an AclSet object.

AclResoler  - This class is used to manage all Acl- and AclSets objects.

"""


class AclSet(list):
    """
    This is a container for ACL entries.
    """
    location = None

    def __init__(self, location):
        self.location = location

    def getLocation(self):
        return(self.location)

    def add(self, item):
        """
        Adds a new acl object to this aclSet.
        """
        if not isinstance(item, Acl):
            raise TypeError('item is not of type %s' % Acl)

        if item.priority == None:
            item.priority = len(self)

        self.append(item)

        # Sort Acl items by id
        sorted(self, key=lambda item: item.priority)


class Acl(object):
    """
    The Acl class contains list of action for a set of members.
    These Acl classes can then be bundled and attached to a ldap base using
    the aclSet class.
    """
    priority = None

    ONE = 1
    SUB = 2
    PSUB = 3
    RESET = 4

    members = None
    actions = None
    acl_type = None

    def __init__(self, acl_type):

        if acl_type not in (Acl.ONE, Acl.SUB, Acl.PSUB, Acl.RESET):
            raise(Exception("Invalid ACL type given"))

        self.actions = []
        self.locations = []
        self.members = []
        self.acl_type = acl_type

    def addMember(self, member):
        """
        Adds a new member to this acl.
        """
        if type(member) != str:
            raise(Exception("Member should be of type str!"))
        self.members.append(member)

    def addMembers(self, members):
        """
        Adds a list of new members to this acl.
        """
        if type(members) != list or len(members) == 0:
            raise(Exception("Requires a list of members!"))

        for member in members:
            self.addMember(member)

    def addAction(self, action, acls, options):
        """
        Adds a new action to this acl.
        """
        acl = {
                'action': action,
                'acls': acls,
                'options': options}
        self.actions.append(acl)

    def getMembers(self):
        """
        Returns the list of members this ACL is valid for.
        """
        return(self.member)

    def match(self, user, action, acls, options={}):
        """
        Check of the requested user, action and the action options match this
        acl-object.
        """
        if user in self.members:
            for act in self.actions:

                # check for # and * placeholders
                test_act = re.escape(act['action'])
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

    def getType(self):
        """
        Returns the type of an ACL.
        SUB, PSUB, RESET, ...
        """
        return(self.acl_type)


class AclResolver(object):

    aclSets = []
    ldapBase = ""

    def __init__(self, ldapBase):
        self.ldapBase = ldapBase
        do_whatever = self.load('agent.acl')

    def addAclSet(self, acl):
        """
        Adds an aclSet object to the list of active-acl rules.
        """
        self.aclSets.append(acl)


    def save(self):

        ret = {}
        for aclSet in self.aclSets:
            ret[aclSet.location] = []
            for acl in aclSet:
                entry = {'actions': acl.actions,
                         'members': acl.members,
                         'priority': acl.priority,
                         'acl_type': acl.acl_type}
                ret[aclSet.location]. append(entry)

        with open('acl.json', 'w') as f:
            import json
            json.dump(ret, f, indent=2)


    def refreshAcls(self):
        """
        Re-reads the permission settings from the ldap server.

        It resolves ACL roles and transforms acl-definitions into AclSet and Acl
        objects. Which can then be used by this class.
        """
        pass

    def load(self, filename):
        try:
            return json.loads(open(filename).read())

        except IOError:
            return {}


    def save(self, filename, acl):
        with open(filename, 'w') as f:
            f.write(json.dumps(acl, indent=4))

    def getPermissions(self, user, location, action, acls, options={}):
        """
        Check permissions for a given user and a location.
        """

        # Collect all acls matching the where statement
        allowed = False
        reset = False

        print "ACL: Checking acl for %s/%s/%s" % (user, location, str(action))

        # Remove the first part of the dn, until we reach the ldap base.
        while self.ldapBase in location:

            # Check acls for each acl set.
            for aclSet in self.aclSets:

                # Skip acls that do not match the current ldap location.
                if location != aclSet.location:
                    continue

                # Resolve ACLs.
                for acl in aclSet:
                    if acl.match(user, action, acls, options):
                        print "ACL: Found matching acl in '%s'!" % location
                        if acl.getType() == Acl.RESET:
                            print "ACL:  Acl reset for action '%s'!" % (action)
                            reset = True
                        elif acl.getType() == Acl.PSUB:
                            print "ACL:  Found permanent acl for action '%s'!" % (action)
                            return True
                        elif acl.getType() in (Acl.SUB, ) and not reset:
                            print "ACL:  Found acl for action '%s'!" % (action)
                            return True

            # Remove the first part of the dn
            location = ','.join(ldap.dn.explode_dn(location)[1::])

        return(allowed)
