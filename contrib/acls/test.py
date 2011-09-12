import os
from acl import Acl, AclSet, AclRole, AclRoleEntry, AclResolver

from gosa.common import Environment
Environment.config = "test-acl.conf"
Environment.noargs = True

resolver = None

if not os.path.exists("agent.acl"):

    # Instantiate the ACl resolver
    resolver = AclResolver()

    # Create a new AclRole
    role = AclRole('role1')
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'priority=1', 'rwx', {})
    role.add(acl)
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'priority=2', 'rwx', {})
    role.add(acl)
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'priority=3', 'rwx', {})
    role.add(acl)
    resolver.add_acl_role(role)

    # Create a new AclRole again
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'gosa.objects.Person.userPassword', 'rwx', {})
    acl.add_action(u'gosa.objects.Person.username', 'rwx', {})
    acl.add_action(u'gosa.objects.Person.phone', 'rwx', {})
    role123 = AclRole('role123')
    role123.add(acl)
    resolver.add_acl_role(role123)

    # Create a new AclRole
    role2 = AclRole('role2')
    acl = AclRoleEntry(role=role)
    role2.add(acl)
    resolver.add_acl_role(role2)

    # Define some ACls
    acl1 = Acl(scope=Acl.SUB)
    acl1.add_members([u'cajus', u'hickert'])
    acl1.add_action(u'gosa.*.cancelEvent', 'rwx', {})
    aclSet1 = AclSet(u"dc=gonicus,dc=de")
    aclSet1.add(acl1)

    # ...
    acl2 = Acl(role = role)
    acl3 = Acl(scope=Acl.SUB)
    acl3.add_members([u'cajus'])
    acl3.add_action(u'gosa.scheduler.cancelEvent', 'rwx', {})
    aclSet2 = AclSet(u"ou=technik,dc=intranet,dc=gonicus,dc=de")
    aclSet2.add(acl2)
    aclSet2.add(acl3)

    resolver.add_acl_set(aclSet1)
    resolver.add_acl_set(aclSet2)

    # Use the created ACL role
    acl = Acl(role=role2)
    acl.add_members([u"cajus", u"Wursty"])
    resolver.add_acl_to_set(u"ou=technik,dc=intranet,dc=gonicus,dc=de", acl)

    resolver.save_to_file()

# Load definition from file
if not resolver:
    resolver = AclResolver()

deps = ['ou=1,ou=technik,dc=intranet,dc=gonicus,dc=de',
        'ou=technik,dc=intranet,dc=gonicus,dc=de',
        'dc=intranet,dc=gonicus,dc=de',
        'dc=gonicus,dc=de']

actions = ["gosa.scheduler.cancelEvent"]
options = {'owner': 'hickert'}
acls = 'rw'

for dep in deps:
    for user in ('cajus','hickert'):

        for action in actions:
            if(resolver.get_permissions(user, dep, action, acls, options)):
                print "|---> %s darf %s in %s" % (user, action, dep)
                #print ""
                pass
            else:
                print "|---> %s darf NICHT %s in %s" % (user, action, dep)
                #print ""
                pass

print resolver.get_permissions('cajus',
    'ou=1,ou=technik,dc=intranet,dc=gonicus,dc=de',
    'gosa.objects.Person.userPassword', 'rw')




# print "#"* 50
#
# for location in resolver.list_acl_locations():
#     print "Removing: %s" % location
#     resolver.remove_aclset_by_location(location)
#
# for role_name in resolver.list_role_names():
#     print "Removing: %s" % role_name
#     resolver.remove_role(role_name)

# print "#"* 50
# print "Remove all acl entries for each AclSet"
# for aclset in resolver.list_acls():
#     aclset.remove_acls_for_user('cajus')
#     while len(aclset):
#         entry = aclset[0]
#         aclset.remove(entry)
#
resolver.save_to_file()

for aclset in resolver.list_acls():
    print aclset
    print 

for name, aclset in resolver.list_roles().items():
    print aclset
    print 



