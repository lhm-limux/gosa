from libgroupware.util import isMailAddress
import unittest

class TestExchangeFunctions(unittest.TestCase):

    def test_isMailAddress(self):
        self.assertFalse(isMailAddress(''))
        self.assertTrue(isMailAddress('valid@test.com'))
        self.assertFalse(isMailAddress('invalid!test.com'))
        self.assertTrue(isMailAddress('j@jj.ca'))
        self.assertTrue(isMailAddress('test@tv.info'))
        self.assertFalse(isMailAddress('haha.hoho.@somedomain.de">class="prettyprint">haha.hoho.@somedomain.de'))


if __name__ == '__main__':
    unittest.main()
