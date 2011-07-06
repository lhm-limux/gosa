# -*- coding: utf-8 -*-
import ldap.filter

print ldap.filter.filter_format("(&(objectClass=%s)(cn=%s))", ['posixAccount', 'ganz&oder)so'])
print ldap.filter.escape_filter_chars('ganz&oder)so')
