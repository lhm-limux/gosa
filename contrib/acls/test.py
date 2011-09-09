from acl import Acl, AclSet, AclRole, AclRoleEntry, AclResolver
import os

if not os.path.exists("agent.acl"):

    # Instantiate the ACl resolver
    resolver = AclResolver.get_instance()

    # Create a new AclRole
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'gosa.objects.Person.userPassword', 'rwx', {})
    acl.add_action(u'gosa.objects.Person.username', 'rwx', {})
    acl.add_action(u'gosa.objects.Person.phone', 'rwx', {})
    role = AclRole('role1')
    role.add(acl)
    resolver.add_acl_role(role)

    # Create a new AclRole
    role2 = AclRole('role2')
    acl = AclRoleEntry(scope=Acl.SUB)
    acl.add_action(u'test.userPassword', 'rwx', {})
    role2.add(acl)
    acl = AclRoleEntry()
    acl.use_role(role)
    role2.add(acl)
    resolver.add_acl_role(role2)

    ## Define some ACls 
    #acl1 = Acl(scope=Acl.SUB)
    #acl1.add_members([u'cajus', u'hickert'])
    #acl1.add_action(u'gosa.*.cancelEvent', 'rwx', {})
    #aclSet1 = AclSet(u"dc=gonicus,dc=de")
    #aclSet1.add(acl1)

    ## ...
    #acl2 = Acl(scope=Acl.RESET)
    #acl2.add_members([u'hickert'])
    #acl2.add_action(u'gosa.scheduler.cancelEvent', 'rwx', {'owner': 'hickert'})
    #acl3 = Acl(scope=Acl.SUB)
    #acl3.add_members([u'cajus'])
    #acl3.add_action(u'gosa.scheduler.cancelEvent', 'rwx', {})
    #aclSet2 = AclSet(u"ou=technik,dc=intranet,dc=gonicus,dc=de")
    #aclSet2.add(acl2)
    #aclSet2.add(acl3)

    #resolver.add_acl_set(aclSet1)
    #resolver.add_acl_set(aclSet2)

    # Use the created ACL role
    acl = Acl(role=role2)
    acl.add_members([u"cajus"])
    aclSet = AclSet(u"ou=technik,dc=intranet,dc=gonicus,dc=de")
    aclSet.add(acl)
    resolver.add_acl_set(aclSet)

    resolver.save_to_file()

# Load definition from file
resolver = AclResolver.get_instance()

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

resolver.save_to_file()




print "#"* 50

for rolename, role in resolver.list_roles().items():
    print rolename, role
    resolver.remove_role(role)
