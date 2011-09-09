from acl import Acl, AclSet, AclRole, AclResolver
import os

if not os.path.exists("agent.acl"):
    acl1 = Acl(Acl.SUB)
    acl1.add_members([u'cajus', u'hickert'])
    acl1.add_action(u'gosa.*.cancelEvent', 'rwx', {})
    aclSet1 = AclSet(u"dc=gonicus,dc=de")
    aclSet1.add(acl1)

    acl2 = Acl(Acl.RESET)
    acl2.add_members([u'hickert'])
    acl2.add_action(u'gosa.scheduler.cancelEvent', 'rwx', {'owner': 'hickert'})
    acl3 = Acl(Acl.SUB)
    acl3.add_members([u'cajus'])
    acl3.add_action(u'gosa.scheduler.cancelEvent', 'rwx', {})
    aclSet2 = AclSet(u"ou=technik,dc=intranet,dc=gonicus,dc=de")
    aclSet2.add(acl2)
    aclSet2.add(acl3)

    resolver = AclResolver.get_instance()
    resolver.add_acl_set(aclSet1)
    resolver.add_acl_set(aclSet2)


    # Create a new AclRole
    acl = Acl(Acl.SUB)
    acl.add_members([u'hickert', u'cajus'])
    acl.add_action(u'gosa.objects.Person.userPassword', 'rwx', {})

    role = AclRole('role1')
    role.add(acl)
    resolver.add_acl_role(role)

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
                print ""
                pass
            else:
                print "|---> %s darf NICHT %s in %s" % (user, action, dep)
                print ""
                pass

resolver.save_to_file()
