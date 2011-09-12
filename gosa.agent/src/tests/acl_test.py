# -*- coding: utf-8 -*-
import unittest
import os
from gosa.agent.acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver
from gosa.common import Environment


class TestACLResolver(unittest.TestCase):

    env = None

    def setUp(self):
        """ Stuff to be run before every test """
        Environment.config = "test-acl.conf"
        Environment.noargs = True
        self.env = Environment.getInstance()
        self.resolver = ACLResolver()


if __name__ == '__main__':
    unittest.main()
