import os
import unittest
from gosa.common import Environment
from gosa.agent.plugins.goto.network import NetworkUtils

Environment.reset()
Environment.config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.conf")
Environment.noargs = True

class TestGOtoPlugin(unittest.TestCase):

    def test_mksmbhash(self):
        #TODO: mockup env
        network = NetworkUtils()
        #networkCompletion
        #getMacManufacturer
        #self.assertEqual(sambaUtils.mksmbhash('secret'), '552902031BEDE9EFAAD3B435B51404EE:878D8014606CDA29677A44EFA1353FC7')
        #self.assertEqual(sambaUtils.mksmbhash(''), 'AAD3B435B51404EEAAD3B435B51404EE:31D6CFE0D16AE931B73C59D7E0C089C0')
        #self.assertRaises(TypeError, sambaUtils.mksmbhash, None, '')

if __name__ == "__main__": 
    unittest.main()
