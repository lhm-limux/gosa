#-*- coding: utf-8 -*-
import os
import test_NoseXUnit

import nosexunit.tools as ntools
import nosexunit.excepts as nexcepts

class TestCreate(test_NoseXUnit.TestCase):
    
    def test_not_exists(self):
        folder = os.path.join(self.work, 'foo')
        ntools.create(folder)
        self.assertTrue(os.path.isdir(folder))

    def test_exists_but_file(self):
        folder = os.path.join(self.work, 'foo')
        open(folder, 'w').close()
        self.assertRaises(nexcepts.ToolError, ntools.create, folder)

if __name__=="__main__":
    test_NoseXUnit.main()