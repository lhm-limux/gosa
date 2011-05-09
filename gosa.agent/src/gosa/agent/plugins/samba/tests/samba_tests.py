import unittest
from gosa.agent.plugins.samba.utils import SambaUtils

class TestSambaPlugin(unittest.TestCase):

    def test_mksmbhash(self):
        sambaUtils = SambaUtils(None)
        self.assertEqual(sambaUtils.mksmbhash('secret'), '552902031BEDE9EFAAD3B435B51404EE:878D8014606CDA29677A44EFA1353FC7')
        self.assertEqual(sambaUtils.mksmbhash(''), 'AAD3B435B51404EEAAD3B435B51404EE:31D6CFE0D16AE931B73C59D7E0C089C0')
        self.assertRaises(TypeError, sambaUtils.mksmbhash, None, '')

if __name__ == "__main__": 
    unittest.main()
