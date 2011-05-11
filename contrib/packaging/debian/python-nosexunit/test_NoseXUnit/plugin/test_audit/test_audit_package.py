#-*- coding: utf-8 -*-
import os
import test_NoseXUnit

import nosexunit.tools as ntools
import nosexunit.excepts as nexcepts

class TestAuditPackage(test_NoseXUnit.PluginTestCase):
    
    def setUpCase(self):
        content = """
def hello():
    return "hello"
"""
        package = test_NoseXUnit.Package('foo_1')
        package.append(test_NoseXUnit.Module('foo_2', content))
        package.save(self.source)
        self.suitepath = self.source
        self.setUpCore(self.core_target, self.source)
        self.setUpAudit(self.audit_target)

    def test(self):
        self.assertExists(os.path.join(self.audit_target, 'foo_1-code.html'))
        self.assertExists(os.path.join(self.audit_target, 'foo_1-detail.html'))
        self.assertExists(os.path.join(self.audit_target, 'foo_1.foo_2-code.html'))
        self.assertExists(os.path.join(self.audit_target, 'foo_1.foo_2-detail.html'))

if __name__=="__main__":
    test_NoseXUnit.main()
