# -*- coding: utf-8 -*-
import ldap.dn

# Some bits to shredd...
dn = u"cn=Alfred Schröder+uid=fred,ou=Kommunalpolitik\, Geschäftsführung,dc=gonicus,dc=de"

# Remove unicode, because the ldap module does not like it
dn = dn.encode('utf-8')

print "Process:", dn

# Example splitting
print "Split:"
print ldap.dn.str2dn(dn, flags=ldap.DN_FORMAT_LDAPV3)

print "Explode:"
print ldap.dn.explode_dn(dn, flags=ldap.DN_FORMAT_LDAPV3)
print ldap.dn.explode_dn(dn, notypes=True, flags=ldap.DN_FORMAT_LDAPV3)

print "Explode RDN:"
print ldap.dn.explode_rdn("cn=Cajus Pollmeier+uid=cajus")

print "Build DN:"
#print ldap.AVA_BINARY
#print ldap.AVA_STRING
#print ldap.AVA_NULL
#print ldap.AVA_NONPRINTABLE
s = ldap.dn.dn2str([[("cn", "Alfred Schröder", 4), ("uid", "fred", 4)], [('dc', 'gonicus', 4)], [('dc', 'de', 4)]])
print s
print ldap.dn.str2dn(s, flags=ldap.DN_FORMAT_LDAPV3)

