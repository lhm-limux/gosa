# ldap.cidict -> case insensitive dictionary
# attrs = cidict(attrs)

from ldap.cidict import cidict

print cidict({'cn': 'Klaus Mustermann', 'mailAlternateAddress': 'klaus@mustermann.person'})
