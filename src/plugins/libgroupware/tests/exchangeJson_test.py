\
from libgroupware.exchange.main import MSExchange
from gosa.common.env import Environment
import unittest
import traceback
import pprint
import win32api
from win32com.mapi import mapi, mapiutil, mapitags
from libgroupware.base import Groupware, GroupwareObjectAlreadyExists, \
GroupwareNoSuchObject, GroupwareValueError, ACTIVE, INACTIVE, PENDING, \
RIGHTS_READ, RIGHTS_WRITE, GroupwareTimeout
from time import time, sleep
import json 

"""
TODO:   GroupwareObjectAlreadyExists check if this exceptions
        has got to be tested somewhere here, too
"""

class jsonHelperClass:
    
    publicProperty1 = "string public"
    _protectedProperty1 = "string protected"
    __privateProperty1 = "string privare"
    
    def doSomething(self):
        print self.publicProperty1
        print self._protectedProperty1
        print self.__privateProperty1

class TestExchangeFunctions(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dictToJson(self):
        dictA = {"property1": "sting", "property2": [1,2,3,4]}
        encDictA = json.dumps(dictA)
        print encDictA
        decDictA = json.loads(encDictA)
        print decDictA

        self.assertEquals(decDictA, dictA )

    def test_objectToJson(self):
        h = jsonHelperClass()

        encDictA = json.dumps(h)
        print encDictA
        decDictA = json.loads(encDictA)
        print decDictA

        self.assertEquals(h, decDictA)

