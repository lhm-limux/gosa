# -*- coding: utf-8 -*-
import unittest
import os
from gosa.agent.acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver
from gosa.common import Environment


class TestACLResolver(unittest.TestCase):

    env = None
    ldap_base = None

    def setUp(self):
        """ Stuff to be run before every test """
        Environment.config = "test-acl.conf"
        Environment.noargs = True
        self.env = Environment.getInstance()
        self.resolver = ACLResolver()
        self.ldap_base = self.resolver.base

    def test_roles(self):

        # Create an ACLRole
        role = ACLRole('role1')
        acl = ACLRoleEntry(scope=ACL.ONE)
        acl.add_action('com.gosa.factory','rwx')
        role.add(acl)
        self.resolver.add_acl_role(role)

        # Use the recently created role. 
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(role=role)
        acl.add_members([u'tester1'])
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is able to read!")

    def test_role_recursion(self):
        pass

    def test_acl_priorities(self):

        # Set up a RESET and a ONE or SUB scoped acl for the same location
        # and check which wins.

        # Create acls with scope SUB
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        acl.set_priority(100)
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")

        # Now add the RESET acl
        acl = ACL(scope=ACL.RESET)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        acl.set_priority(99)
        aclset.add(acl)

        # Check the permissions to be sure that they are set correctly
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is able to read!")

    def test_acls_scope_reset(self):

        # Create acls with scope SUB
        base = "dc=a," + self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.SUB)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check for acls for the base, should return False
        base = self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is able to read!")

        # Check for acls for the tree we've created acls for.
        base = "dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")

        # Check for acls for one level above the acl definition
        base = "dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")

        # Check for acls for two levels above the acl definition
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")

        # ------
        # Now add the ACL.RESET
        # ------
        base = "dc=b,dc=a," + self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.RESET)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        aclset.add(acl)

        self.resolver.add_acl_set(aclset)

        # Check for acls for the tree we've created acls for.
        # Should return True
        base = "dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")

        # Check for acls for one level above the acl definition
        # Should return False
        base = "dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is able to read!")

        # Check for acls for two levels above the acl definition
        # Should return False
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is able to read!")

    def test_acls_scope_sub(self):

        # Create acls with scope SUB
        base = "dc=a," + self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.SUB)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check for read, write, create, execute permisions
        base = "dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','w'),
                "User is not able to write!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','x'),
                "User is not able to execute!")
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','d'),
                "User is able to delete, this acl was not defined before!")

        # Check for permissions one level above the location we've created acls for.
        # This should return True.
        base = "dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is not able to read, this is wrong!")

        # Check for permissions tow levels above the location we've created acls for.
        # This should return True too.
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is not able to read, this is wrong!")

        # Check for permissions one level below the location we've created acls for.
        # This should return False.
        base = self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is able to read, this is wrong!")

    def test_acls_scope_one(self):

        # Create acls with scope ONE
        base = "dc=a," + self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check for read, write, create, execute permisions
        base = "dc=a," + self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','w'),
                "User is not able to write!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','x'),
                "User is not able to execute!")
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','d'),
                "User is able to delete, this acl was not defined before!")

        # Check for permissions one level above the location we've created acls for.
        base = "dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is able to read, this is wrong!")

        # Check for permissions one level below the location we've created acls for.
        base = self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is able to read, this is wrong!")


if __name__ == '__main__':
    unittest.main()
