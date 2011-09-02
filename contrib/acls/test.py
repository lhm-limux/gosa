import re


#TODO: The permission types (rwcdm) are not checked yet.
#TODO: The permission options (onwer=cajus) are not checked yet.
#TODO: Think about ldap relations, how to store and load objects.



"""
This is a collection of classes that can manager Access control lists.

AclSet      - Is a container class for Acl objects. An AclSet-object can be attached
              to ldap organizationalUnits to restrict permissions for a set of
              users.
Acl         - This class represent a single ACL rule, these Acl objects can be
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
        if not isinstance(item, Acl):
            raise TypeError, 'item is not of type %s' % Acl

        if item.priority == None:
            item.priority = len(self)

        super(AclSet, self).append(item)

        # Sort Acl items by id
        sorted(self, key=lambda item: item.priority)


class Acl(object):

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

        if type(member) != str:
            raise(Exception("Member should be of type str!"))
        self.members.append(member)

    def addMembers(self, members):

        if type(members) != list or len(members) == 0:
            raise(Exception("Requires a list of members!"))

        for member in members:
            self.addMember(member)

    def addAction(self, action, acls, options):
        acl = { 'action': action,
                'acls': acls,
                'options': options}
        self.actions.append(acl)

    def getMembers(self):
        return(self.member)

    def match(self, member, action, options):
        allowd = False

        if member in self.members:
            for act in self.actions:

                # check for # and * placeholders
                test_act = re.escape(act['action'])
                test_act = re.sub(r'(^|\\.)(\\\*)(\\.|$)', '\\1.*\\3', test_act)
                test_act = re.sub(r'(^|\\.)(\\#)(\\.|$)', '\\1[^\.]*\\3', test_act)

                # Check if the action string matches the acl-action definition
                if re.match(test_act, action):
                    return True

        return False

    def getType(self):
        return(self.acl_type)


class AclResolver(object):

    aclSets = []

    def __init__(self):
        self.refreshAcls()

    def addAclSet(self, acl):
        self.aclSets.append(acl)

    def refreshAcls(self):
        pass

    def getPermissions(self, member, location, action, options= {}):

        # Collect all acls matching the where statement
        allowed = False
        reset = False
        while "," in location:
            for aclSet in self.aclSets:

                if location != aclSet.location:
                    continue

                for acl in aclSet:
                    if acl.match(member, action, options):
                        if acl.getType() == Acl.RESET:
                            reset = True
                        elif acl.getType() == Acl.PSUB:
                            allowed = True
                        elif acl.getType() in (Acl.SUB,) and not reset:
                            allowed = True

            #TODO Use ldap dn split
            location = re.sub("^[^,]+,","",location)

        return(allowed)


acl1 = Acl(Acl.SUB)
acl1.addMembers(['cajus', 'hickert'])
acl1.addAction('gosa.*.cancelEvent', ['r','w','x'], {})
aclSet1 = AclSet("dc=gonicus,dc=de")
aclSet1.add(acl1)

acl2 = Acl(Acl.RESET)
acl2.addMembers(['hickert'])
acl2.addAction('gosa.scheduler.cancelEvent', ['r','w','x'], {})
acl3 = Acl(Acl.SUB)
acl3.addMembers(['cajus'])
acl3.addAction('gosa.scheduler.cancelEvent', ['r','w','x'], {})
aclSet2 = AclSet("ou=technik,dc=intranet,dc=gonicus,dc=de")
aclSet2.add(acl2)
aclSet2.add(acl3)

resolver = AclResolver()
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

        for action in actions:
            if(resolver.getPermissions(user,dep,action)):
                print " >%s darf %s" % (user,action)
                pass
            else:
                print " >%s darf %s nicht!!!" % (user,action)
                pass

