import ldap

con = ldap.initialize("ldap://vm-ldap.intranet.gonicus.de")
con.protocol = ldap.VERSION3
con.simple_bind_s()

print con.search_ext_s("dc=gonicus,dc=de", ldap.SCOPE_SUBTREE, 'uid=*',
        ['uid'], timeout=10, sizelimit=1)

con.unbind()
