import sys,ldap,ldap.resiter

class MyLDAPObject(ldap.ldapobject.LDAPObject,ldap.resiter.ResultProcessor):
  pass

l = MyLDAPObject('ldap://vm-ldap.intranet.gonicus.de')

# Asynchronous search method
msg_id = l.search('dc=gonicus,dc=de',ldap.SCOPE_SUBTREE,'(objectClass=*)')

for res_type,res_data,res_msgid,res_controls in l.allresults(msg_id):
  for dn,entry in res_data:
    # process dn and entry
    print dn,entry['objectClass']
