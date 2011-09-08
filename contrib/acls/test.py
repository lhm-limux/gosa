import re
import ldap


#TODO: The permission types (rwcdm) are not checked yet.
#TODO: The permission options (onwer=cajus) are not checked yet.
#TODO: Think about ldap relations, how to store and load objects.
#TODO: Groups are not supported yet
#TODO: What about object groups, to be able to inlcude clients?
#TODO: Use ldap dn split



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

    def add(self, item):
        """
        Adds a new acl object to this aclSet.
        """
        if not isinstance(item, Acl):
            raise TypeError, 'item is not of type %s' % Acl

        if item.priority == None:
            item.priority = len(self)

        super(AclSet, self).append(item)

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
        acl = { 'action': action,
                'acls': acls,
                'options': options}
        self.actions.append(acl)

    def getMembers(self):
        """
        Returns the list of members this ACL is valid for.
        """
        return(self.member)

    def match(self, member, action, acls, options = {}):
        """
        Check of the requested user, action and the action options match this
        acl-object.
        """
        allowd = False

        if member in self.members:
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
                    if entry not in options:
                        print "Option '%s' is missing" % entry
                        continue

                    if act['options'][entry] != options[entry]:
                        print "Option '%s:%s' does not match" % (entry,
                                act['options'][entry])
                        continue

                return(True)


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
        self.ldapBase = ldapBase;

    def addAclSet(self, acl):
        """
        Adds an aclSet object to the list of active-acl rules.
        """
        self.aclSets.append(acl)

    def refreshAcls(self):
        """
        Re-reads the permission settings from the ldap server.
        """
        pass

    def getPermissions(self, member, location, action, acls, options= {}):
        """
        Check permissions for a given user(member) and a location.
        """

        # Collect all acls matching the where statement
        allowed = False
        reset = False

        # Remove the first part of the dn, until we reach the ldap base.
        while self.ldapBase in location:

            # Check acls for each acl set.
            for aclSet in self.aclSets:

                # Skip acls that do not match the current ldap location.
                if location != aclSet.location:
                    continue

                # Resolve ACLs.
                for acl in aclSet:
                    if acl.match(member, action, acls, options):
                        if acl.getType() == Acl.RESET:
                            reset = True
                        elif acl.getType() == Acl.PSUB:
                            allowed = True
                        elif acl.getType() in (Acl.SUB,) and not reset:
                            allowed = True

            # Remove the first part of the dn
            location =  ','.join(ldap.dn.explode_dn(location)[1::])

        return(allowed)


acl1 = Acl(Acl.SUB)
acl1.addMembers(['cajus', 'hickert'])
acl1.addAction('gosa.*.cancelEvent', ['r','w','x'], {})
aclSet1 = AclSet("dc=gonicus,dc=de")
aclSet1.add(acl1)

acl2 = Acl(Acl.RESET)
acl2.addMembers(['hickert'])
acl2.addAction('gosa.scheduler.cancelEvent', ['r','w','x'], {'owner': 'hickert'})
acl3 = Acl(Acl.SUB)
acl3.addMembers(['cajus'])
acl3.addAction('gosa.scheduler.cancelEvent', ['r','w','x'], {})
aclSet2 = AclSet("ou=technik,dc=intranet,dc=gonicus,dc=de")
aclSet2.add(acl2)
aclSet2.add(acl3)

resolver = AclResolver("dc=gonicus,dc=de")
resolver.addAclSet(aclSet1)
resolver.addAclSet(aclSet2)

deps = [
        'ou=1,ou=technik,dc=intranet,dc=gonicus,dc=de',
        'ou=technik,dc=intranet,dc=gonicus,dc=de',
        'dc=intranet,dc=gonicus,dc=de',
        'dc=gonicus,dc=de']

actions = ["gosa.scheduler.cancelEvent"]

for dep in deps:
    print ""
    print dep
    for user in ('cajus','hickert'):

        options = {'owner': 'hickert'}
        acls = ['r','w']
        for action in actions:
            if(resolver.getPermissions(user, dep, action, acls, options)):
                print "   >%s darf %s" % (user, action)
                pass
            else:
                print "   >%s darf %s nicht!!!" % (user,action)
                pass

