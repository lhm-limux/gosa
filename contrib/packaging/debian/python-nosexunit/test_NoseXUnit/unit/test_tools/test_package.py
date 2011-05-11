#-*- coding: utf-8 -*-
import test_NoseXUnit

import nosexunit.tools as ntools

class TestPackage(test_NoseXUnit.TestCase):
    
    def assertPackage(self, package):
        self.assertEquals(package.full(), ntools.package(package.path()))
    
    def test_package(self):
        self.assertPackage(test_NoseXUnit.Package('foo').save(self.source))

    def test_module(self):
        self.assertPackage(test_NoseXUnit.Module('foo').save(self.source))

    def test_package_in_package(self):
        p1 = test_NoseXUnit.Package('foo_1')
        p2 = test_NoseXUnit.Package('foo_2')
        p1.append(p2)
        p1.save(self.source)
        self.assertPackage(p2)

    def test_module_in_package(self):
        p = test_NoseXUnit.Package('foo_1')
        m = test_NoseXUnit.Module('foo_2')
        p.append(m)
        p.save(self.source)
        self.assertPackage(m)
        
if __name__=="__main__":
    test_NoseXUnit.main()