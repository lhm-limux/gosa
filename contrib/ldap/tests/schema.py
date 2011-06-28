import ldap
import ldap.schema

con = ldap.initialize("ldap://vm-ldap.intranet.gonicus.de")
con.protocol = ldap.VERSION3
con.simple_bind_s()
res = con.search_s('cn=subschema', ldap.SCOPE_BASE, 'objectClass=*', ['*', '+'])[0][1]

subschema = ldap.schema.SubSchema(res)
cn_attr = subschema.get_obj( ldap.schema.AttributeType, 'cn' )
print cn_attr.names
print cn_attr.desc
print cn_attr.oid

oc_list = ['account', 'simpleSecurityObject']
oc_attrs = subschema.attribute_types( oc_list )
must_attrs = oc_attrs[0]
may_attrs = oc_attrs[1]
for (oid, attr_obj) in must_attrs.iteritems():
    print "Must have %s" % attr_obj.names[0]
for (oid, attr_obj) in may_attrs.iteritems():
    print "May have %s" % attr_obj.names[0]

oc_obj = subschema.get_obj( ldap.schema.ObjectClass, 'account' )
print oc_obj.__dict__

at_obj = subschema.get_obj( ldap.schema.AttributeType, 'uid' )
print at_obj.__dict__

con.unbind()
