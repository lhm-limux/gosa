from acl import Acl, AclSet, AclResolver

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
options = {'owner': 'hickert'}
acls = ['r','w']

for dep in deps:
    for user in ('cajus','hickert'):

        for action in actions:
            if(resolver.getPermissions(user, dep, action, acls, options)):
                print "|---> %s darf %s in %s" % (user, action, dep)
                print ""
                pass
            else:
                print "|---> %s darf NICHT %s in %s" % (user, action, dep)
                print ""
                pass



resolver.save()
