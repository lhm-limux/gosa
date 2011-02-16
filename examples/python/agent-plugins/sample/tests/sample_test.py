# -*- coding: utf-8 -*-
import unittest
from gosa.common.env import Environment
from sample.module import SampleModule

class TestSampleModule(unittest.TestCase):

    env = None

    def setUp(self):
        """ Stuff to be run before every test """
        Environment.config = "sample_test.conf"
        Environment.noargs = True
        self.env = Environment.getInstance()

        self.plugin = SampleModule()

    def tearDown(self):
        """ Stuff to be run after every test """
        pass

    def test_hello(self):
        self.assertEquals(self.plugin.hello("developer"), "Hello developer!")
        self.assertEquals(self.plugin.hello(), "Hello unknown!")

    def test_hello2(self):
        self.assertEquals(self.plugin.hello2(), '"Hello world!"')

if __name__ == '__main__':
    unittest.main()
