import unittest
from gosa.agent.plugins.samba.utils import SambaUtils
import os
from acl import ACL, ACLSet, ACLRole, ACLRoleEntry, ACLResolver

from gosa.common import Environment
Environment.config = "test-acl.conf"
Environment.noargs = True

class TestAclPlugin(unittest.TestCase):
    def test_acl_matching(self):
        self.assertEquals(1,2, "verdammt")


if __name__ == "__main__":
        unittest.main()


