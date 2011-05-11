#-*- coding: utf-8 -*-
import test_NoseXUnit

import nosexunit.tools as ntools

class TestSplit(test_NoseXUnit.TestCase):
    
    def test_both(self):
        bn, ext = ntools.split('hello.dat')
        self.assertEquals('hello', bn)
        self.assertEquals('dat', ext)
        
    def test_only_bn(self):
        bn, ext = ntools.split('hello')
        self.assertEquals('hello', bn)
        self.assertNone(ext)
        
    def test_two_dot(self):
        bn, ext = ntools.split('hello.hbm.xml')
        self.assertEquals('hello.hbm', bn)
        self.assertEquals('xml', ext)
        
if __name__=="__main__":
    test_NoseXUnit.main()