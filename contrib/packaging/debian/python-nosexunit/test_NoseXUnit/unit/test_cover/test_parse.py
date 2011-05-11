#-*- coding: utf-8 -*-
import test_NoseXUnit

import nosexunit.cover as cover

class TestParse(test_NoseXUnit.TestCase):
    
    def test_1(self):
        content = """Name    Stmts   Exec  Cover   Missing
-------------------------------------
foo         4      3    75%   5
"""
        sources = cover.parse(content)
        self.assertEquals(1, len(sources))
        source = sources[0]
        self.assertEquals('foo', source.full())
        self.assertEquals(4, source.all())
        self.assertEquals(3, source.exe())
        self.assertEquals(75.0, source.percent())
        self.assertEquals(75.0, sources.percent())

    def test_2(self):
        content = """Name    Stmts   Exec  Cover   Missing
-------------------------------------
foo_1       4      3    75%   5
foo_2       2      1    50%   3
-------------------------------------
TOTAL       6      4    66%   
"""
        sources = cover.parse(content)
        self.assertEquals(2, len(sources))
        self.assertEquals('66.667', '%.3f' % sources.percent())
        
if __name__=="__main__":
    test_NoseXUnit.main()
