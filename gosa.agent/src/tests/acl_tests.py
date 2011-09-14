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
        Environment.config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test-acl.conf")
        Environment.noargs = True
        self.env = Environment.getInstance()
        self.resolver = ACLResolver()
        self.resolver.clear()
        self.ldap_base = self.resolver.base

    def test_role_endless_recursion(self):
        """
        A test which ensures that roles do not refer to each other, creating an endless-recursion.
        role1 -> role2 -> role1
        """
        # Create an ACLRole
        role1 = ACLRole('role1')
        role2 = ACLRole('role2')
        role3 = ACLRole('role3')

        self.resolver.add_acl_role(role1)
        self.resolver.add_acl_role(role2)
        self.resolver.add_acl_role(role3)

        acl1 = ACLRoleEntry(role='role2')
        acl2 = ACLRoleEntry(role='role3')
        acl3 = ACLRoleEntry(role='role1')

        role1.add(acl1)
        role2.add(acl2)
        role3.add(acl3)

        # Use the recently created role.
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(role='role1')
        acl.add_members([u'tester1'])
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertRaises(Exception, self.resolver.check, 'tester1','com.gosa.factory','r',
            location=base)

    def test_user_wildcards(self):
        """
        checks if wildcards/regular expressions can be used for ACL member names
        e.g. to match all users starting with 'gosa_' and ending with '_test'
            acl.add_members([u'^gosa_.*_test$'])
        """

        # Create acls with wildcard # in actions
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'^gosa_.*_test$'])
        acl.add_action('com.gosa.factory','rwx')
        acl.set_priority(100)
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('gosa_user_test','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('gosa__test','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Check the permissions to be sure that they are set correctly
        self.assertFalse(self.resolver.check('gosa_test_testWrong','com.gosa.factory','r',location=base),
                "User is able to read!")

    def test_action_wildcards(self):
        """
        This test checks if ACLs containing wildcard actions are processed correctly.
        e.g.    To match all actions for 'com.' that ends with '.fatcory'
                acl.add_action('com.#.factory','rwx')
        """

        # Create acls with wildcard # in actions
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'tester1'])
        acl.add_action('com.#.factory','rwx')
        acl.set_priority(100)
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")
        self.assertTrue(self.resolver.check('tester1','com.gonicus.factory','r',location=base),
                "User is not able to read!")
        self.assertFalse(self.resolver.check('tester1','com.gonicus.gosa.factory','r',location=base),
                "User is able to read!")

        # Clear created ACL defintions
        self.resolver.clear()

        # Create acls with wildcard * in actions
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'tester1'])
        acl.add_action('com.*.factory','rwx')
        acl.set_priority(100)
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")
        self.assertTrue(self.resolver.check('tester1','com.gonicus.factory','r',location=base),
                "User is not able to read!")
        self.assertTrue(self.resolver.check('tester1','com.gonicus.gosa.factory','r',location=base),
                "User is not able to read!")

    def test_roles(self):
        """
        This test checks if ACLRole objects are resolved correctly.
        """

        # Create an ACLRole
        role = ACLRole('role1')
        acl = ACLRoleEntry(scope=ACL.ONE)
        acl.add_action('com.gosa.factory','rwx')
        role.add(acl)
        self.resolver.add_acl_role(role)

        # Use the recently created role.
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(role='role1')
        acl.add_members([u'tester1'])
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r', location=base),
                "User is able to read!")

    def test_role_recursion(self):
        """
        This test checks if ACLRoles that contain ACLRoles are resolved correctly.
        e.g.
        ACLSet -> Acl -> points to role1
                         role1 -> AclRoleEntry -> points to role 2
                                                  role 2 contains the effective acls.
        """

        # Create an ACLRole
        role1 = ACLRole('role1')
        acl = ACLRoleEntry(scope=ACL.ONE)
        acl.add_action('com.gosa.factory','rwx')
        role1.add(acl)
        self.resolver.add_acl_role(role1)

        # Create another ACLRole wich refers to first one
        role2 = ACLRole('role2')
        acl = ACLRoleEntry(role='role1')
        role2.add(acl)
        self.resolver.add_acl_role(role2)

        # Use the recently created role.
        base = self.ldap_base
        aclset = ACLSet(base)
        acl = ACL(role='role2')
        acl.add_members([u'tester1'])
        aclset.add(acl)
        self.resolver.add_acl_set(aclset)

        # Check the permissions to be sure that they are set correctly
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',
            location=base),
                "User is able to read!")

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
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Now add the RESET acl
        acl = ACL(scope=ACL.RESET)
        acl.add_members([u'tester1'])
        acl.add_action('com.gosa.factory','rwx')
        acl.set_priority(99)
        aclset.add(acl)

        # Check the permissions to be sure that they are set correctly
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is able to read!")

    def test_acls_scope_reset(self):
        """
        This test checks if an ACL entry containing the RESET scope revokes permission correctly.
        """

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
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is able to read!")

        # Check for acls for the tree we've created acls for.
        base = "dc=a," + self.ldap_base
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Check for acls for one level above the acl definition
        base = "dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Check for acls for two levels above the acl definition
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
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
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")

        # Check for acls for one level above the acl definition
        # Should return False
        base = "dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is able to read!")

        # Check for acls for two levels above the acl definition
        # Should return False
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is able to read!")

    def test_acls_scope_sub(self):
        """
        This test checks if permissions with scope SUB are spreed over the subtree correctly.
        A ACL.SUB scope will effect the complete subtree of the location. (In case that no ACL.RESET is used.)
        """

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
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','w',location=base),
                "User is not able to write!")
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','x',location=base),
                "User is not able to execute!")
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','d',location=base),
                "User is able to delete, this acl was not defined before!")

        # Check for permissions one level above the location we've created acls for.
        # This should return True.
        base = "dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "The user is not able to read, this is wrong!")

        # Check for permissions tow levels above the location we've created acls for.
        # This should return True too.
        base = "dc=c,dc=b,dc=a," + self.ldap_base
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "The user is not able to read, this is wrong!")

        # Check for permissions one level below the location we've created acls for.
        # This should return False.
        base = self.ldap_base
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "The user is able to read, this is wrong!")

    def test_acls_scope_one(self):
        """
        This test check if the scope ACL.ONE is populated correclty.
        """

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
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "User is not able to read!")
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','w',location=base),
                "User is not able to write!")
        self.assertTrue(self.resolver.check('tester1','com.gosa.factory','x',location=base),
                "User is not able to execute!")
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','d',location=base),
                "User is able to delete, this acl was not defined before!")

        # Check for permissions one level above the location we've created acls for.
        base = "dc=b,dc=a," + self.ldap_base
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "The user is able to read, this is wrong!")

        # Check for permissions one level below the location we've created acls for.
        base = self.ldap_base
        self.assertFalse(self.resolver.check('tester1','com.gosa.factory','r',location=base),
                "The user is able to read, this is wrong!")


if __name__ == '__main__':
    unittest.main()
