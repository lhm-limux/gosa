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


    def test_simple_acls(self):
        self.resolver.clear()

        base = self.ldap_base

        # Create simple acls with scope ONE
        aclset = ACLSet(base)
        acl = ACL(scope=ACL.ONE)
        acl.add_members([u'tester1', u'tester2'])
        acl.add_action('com.gosa.factory','rwx')
        aclset.add(acl)

        self.resolver.add_acl_set(aclset)

        # Check for read, write, create, execute permisions
        base = self.ldap_base
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "User is not able to read!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','w'),
                "User is not able to write!")
        self.assertTrue(self.resolver.get_permissions('tester1',base,'com.gosa.factory','x'),
                "User is not able to execute!")
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','d'),
                "User is able to delete, this acl was not defined before!")

        # Check for read, write, create, execute permisions
        base = "dc=a," + self.ldap_base
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','r'),
                "The user is able to read, this is wrong!")
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','w'),
                "The user is able to write, this is wrong!")
        self.assertFalse(self.resolver.get_permissions('tester1',base,'com.gosa.factory','x'),
                "The user is able to execute, this is wrong!")

if __name__ == '__main__':
    unittest.main()
