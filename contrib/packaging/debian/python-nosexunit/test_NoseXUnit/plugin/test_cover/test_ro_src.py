#-*- coding: utf-8 -*-
import os
import stat
import test_NoseXUnit

import nosexunit.tools as ntools
import nosexunit.excepts as nexcepts

class TestROSrc(test_NoseXUnit.PluginTestCase):
    '''Check if able to cover read only source files'''
    
    def setUpCase(self):
        content = """
def hello():
    return "hello"
"""
        module = test_NoseXUnit.Module('foo', content)
        module.save(self.source)
        os.chmod(module.path(), stat.S_IREAD)
        content = """
import foo
self.assertEquals('hello', foo.hello())
"""
        test = test_NoseXUnit.TestModule('test_foo', 'TestFoo')
        test.addCustom('test', content)
        test.save(self.source)
        self.suitepath = self.source
        self.setUpCore(self.core_target, self.source)
        self.setUpCover(self.cover_target, clean=False, collect=False)

    def test(self):
        self.assertExists(os.path.join(self.cover_target, 'foo.py,cover'))
        self.assertExists(os.path.join(self.cover_target, 'foo-code.html'))

if __name__=="__main__":
    test_NoseXUnit.main()
