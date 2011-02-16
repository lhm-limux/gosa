# -*- coding: utf-8 -*-
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
"""
TODO: GroupwareObjectAlreadyExists check if this exceptions
      has got to be tested somewhere here, too
"""

Environment.config = "libgroupware.conf"
Environment.noargs = True

class TestExchangeFunctions(unittest.TestCase):

    ExchangeTimeout = 60
    testuserA = "Atest" + win32api.GetUserName() + "A"
    testuserB = "Atest" + win32api.GetUserName() + "B"
    distListName = "ADistTest" + win32api.GetUserName() + "A"

    @classmethod
    def setUpClass(cls):

        # Do something at the beginning of this classes testing.
        """ Stuff to be run before every test """
        env = Environment.getInstance()

        cls.ms = MSExchange()

        cls.__defaultLocation = None
        cls.__defaultRDN = "cn=Users"
        cls.__alternativeRDN = "ou=Testeinheit"

        #==================================================
        # credentials for test user A
        #==================================================
        cls.__defaultUserId_A = cls.testuserA
        cls.__defaultAddress_A = "testStrassenA"

        cls.__primaryEmailAddress_A = cls.testuserA + "@exdom.intranet.gonicus.de"
        cls.__emailAddress_A =  cls.testuserA + "GosaMailtestsA.second@gonicus.de"
        cls.__propertie_A = "propA"
        cls.__defaultUserSet_A = False

        #==================================================
        # credentials for test user B
        #==================================================
        cls.__defaultUserId_B = cls.testuserB
        cls.__defaultAddress_B = "testStrassenB"
        cls.__primaryEmailAddress_B = cls.testuserB + "exdom.intranet.gonicus.de"
        cls.__emailAddress_B = cls.testuserA + "GosaMailtestsA.second@gonicus.de"
        cls.__propertie_B = "propB"
        cls.__primaryEmailAddress_B = "gosaExchangetestB@gonicus.de"
        cls.__defaultUserSet_B = False

        cls.ms.acctAdd(cls.__defaultUserId_A, cls.__primaryEmailAddress_A)
        #checking the status of the account creation process.
        cls.__defaultUserSet_A = True
        for i in range(0, 60):
            if cls.ms.acctGetStatus(cls.__defaultUserId_A)['status'] != PENDING:
                break
            sleep(1)
        else:
            raise GroupwareTimeout("the creating testuserA has thrown a timeout after 60 seconds.")
        cls.ms.acctSetEnabled(cls.__defaultUserId_A, True)

    @classmethod
    def tearDownClass(cls):
        # Do something at the end of this classes testing.

        # All default users created with helper functions will be deleted here
        # this will confirm the workspace to be empty again.
        if cls.__defaultUserSet_A:
           cls.ms.acctDel(cls.__defaultUserId_A)
        
        del(cls.ms)

    def setUp(self):
        """ Run before every test """
        # Nothing to be done here - moved to class startup
        pass

    def tearDown(self):
        """ Run after every test """
        try:                 
            self.ms.distDel(self.distListName)
        except:
            pass

        try:
            self.ms.distDel(self.distListName + "Other")
        except:
            pass
        try:
            self.ms.distDel(self.distListName + "Renamed")
        except:
            pass
    
    def test_distAdd(self):
        id = self.distListName

        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareValueError, self.ms.distAdd, id, "noEmailAddress")
        pMaddress = "DIST" + self.__primaryEmailAddress_A

        self.assertTrue(self.ms.distAdd( id, pMaddress))
        self.assertRaises(GroupwareValueError, self.ms.distAdd, id, pMaddress)

         

    def test_distList(self):
        # Exception GroupwareNoSuchObject
        pMaddress = "DISTsomeVeryspecial" + self.__primaryEmailAddress_A
        id = self.distListName

        aktlist = self.ms.distList()
        print "firstList"
        print aktlist
        aktlistCount = len(aktlist)
        # add another List
        self.ms.distAdd(id, pMaddress)
        # assert listCount is increased by one
        aktlist = self.ms.distList()
        print "secondList"
        print aktlist
        self.assertEquals(len(aktlist), aktlistCount+1)
         
    def test_distRename(self):
        
        pMaddress = "DIST" + self.__primaryEmailAddress_A
        id = self.distListName
        id_new = id + "Renamed"
        id_another = id + "Other"
        # no dist
        self.assertRaises(GroupwareNoSuchObject, self.ms.distRename, id, id_new)

        # add a dist lists
        self.ms.distAdd(id, pMaddress)
        self.ms.distAdd(id_another, pMaddress)
        # not in dist list
        dList = self.ms.distList()
        self.assertFalse(id_new in dList)
        # rename
        self.assertTrue(self.ms.distRename(id, id_new))
        
        # in dist list
        dList = self.ms.distList() 
        print dList
        self.assertTrue(id_new in dList)
        
        # duplicat name
        self.assertRaises(GroupwareValueError, self.ms.distRename, id_another, id_new)
        
        
        # CLEANUP
        self.ms.distDel(id_another)


    def test_distExists(self):
        # Exception GroupwareNoSuchObject
        # distExists(self, id):
        id = self.distListName
        self.assertFalse(self.ms.distExists( id))
        pMaddress = "mydistExists@exdom.intranet.gonicus.de"
        self.ms.distAdd(id, pMaddress)

        self.assertTrue(self.ms.distExists( id))
         

    def test_distDel(self):
        # Exception GroupwareNoSuchObject
        # distDel(self, id):
        id = self.distListName
        self.assertRaises(GroupwareNoSuchObject, self.ms.distDel, id)
        pMaddress = "myDelListDeltest@exdom.intranet.gonicus.de"
        self.ms.distAdd(id, pMaddress)

        self.assertTrue(self.ms.distDel(id))
        self.assertFalse(self.ms.distExists(id))

    def test_distGetPrimaryMailAddress(self):
        # Exception GroupwareNoSuchObject
        # distGetPrimaryMailAddress(self, id):
        id = self.distListName
        pMaddress = "DIST" + self.__primaryEmailAddress_A
        # no such object
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distGetPrimaryMailAddress, id)

        # add dist list
        self.ms.distAdd( id, pMaddress)
        
        # get primary and compare
        mAddress = self.ms.distGetPrimaryMailAddress(id)
        self.assertEquals(mAddress, pMaddress)

    def test_distSetPrimaryMailAddress(self):
        # Exception GroupwareNoSuchObject
        # distSetPrimaryMailAddress(self, id, address):
        id = self.distListName
        newMailAddress = "DIS" + self.__primaryEmailAddress_A
        pMaddress = "DIST" + self.__primaryEmailAddress_A
                
        print "pMAddress:" +  pMaddress
        print "newMailAddress:" + newMailAddress
         
        print win32api.FormatMessage(-2147352567)
        print "second ----------"
        print win32api.FormatMessage(-2147016691)
        # no such object 
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distSetPrimaryMailAddress, id, newMailAddress)
        # add a dist list
        self.ms.distAdd(id, pMaddress)
          
        # set address an already existing one
        self.assertRaises(GroupwareValueError, self.ms.distSetPrimaryMailAddress,
                id, self.__primaryEmailAddress_A)
        
        # setting an prime mail successfully
        self.assertTrue(self.ms.distSetPrimaryMailAddress(id, newMailAddress))

    def test_distSetAlternateMailAddresses(self):
        # Exception GroupwareNoSuchObject
        # distSetAlternateMailAddresses(self, id, addresses):
        id = self.distListName
        primeMail = "DIST" + self.__primaryEmailAddress_A
        altList = ["altOne@gonicus.de", "altOne@gonicus.de"]
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distSetAlternateMailAddresses, id, altList)
        self.ms.distAdd(id, primeMail)

        self.assertTrue(self.ms.distSetAlternateMailAddresses(id, altList))

    def test_distGetAlternateMailAddresses(self):
        # Exception GroupwareNoSuchObject
        # distGetAlternateMailAddresses(self, id):
        id = self.distListName
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distGetAlternateMailAddresses, id)
        primeMail = "DIST" + self.__primaryEmailAddress_A
        self.ms.distAdd(id, primeMail)
        
        altListing = self.ms.distGetAlternateMailAddresses(id)

        self.assertEquals(len(altListing), 0)
        altList = ["altOne@gonicus.de", "altTwo@gonicus.de"]
        self.ms.distSetAlternateMailAddresses(id, altList)
        altListing = self.ms.distGetAlternateMailAddresses(id)
        self.assertEquals(len(altListing), 2)

    def test_distAddAlternateMailAddress(self):
        # Exception GroupwareNoSuchObject
        # distAddAlternateMailAddress(self, id, address):
        id = self.distListName
        primeMail = "DIST" + self.__primaryEmailAddress_A
        altAddress = "altOne" + self.__primaryEmailAddress_A

        # dist does not exist.
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distAddAlternateMailAddress, id, altAddress)
        self.ms.distAdd(id, primeMail)

        self.assertTrue(self.ms.distAddAlternateMailAddress(id, altAddress))

        # Some more assertions?
        self.assertEquals(len(self.ms.distGetAlternateMailAddresses(id)), 1)
            

    def test_distDelAlternateMailAddress(self):
        # Exception GroupwareNoSuchObject
        # distDelAlternateMailAddress(self, id, address):
        id = self.distListName
        primeMail = "DIST" + self.__primaryEmailAddress_A
        altMail = "someAltmail@gonicus.de"
        self.ms.distAdd(id, primeMail)
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distDelAlternateMailAddress, id, altMail)
        self.ms.distAddAlternateMailAddress(id, altMail)
        self.assertTrue(self.ms.distDelAlternateMailAddress(id, altMail))

        self.assertEquals(len(self.ms.distGetAlternateMailAddresses( id)), 0)

    def test_distAddMember(self):
        # Exception GroupwareNoSuchObject
        # distAddMember(self, id, address):
        id = self.distListName
        memberAddr = self.__primaryEmailAddress_A
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distAddMember, id, memberAddr)
        primeMail = "DIST" + self.__primaryEmailAddress_A
        self.ms.distAdd(id, primeMail)

        self.assertTrue(self.ms.distAddMember(id, memberAddr))

    def test_distGetMembers(self):
        # Exception GroupwareNoSuchObject
        # distGetMembers(self, id):
        id = self.distListName
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distGetMembers, id)

        self.ms.distAdd(id, "DIST" + self.__primaryEmailAddress_A)

        self.assertEquals(len(self.ms.distGetMembers(id)), 0)

        memberAddr = self.__primaryEmailAddress_A
        self.ms.distAddMember(id, memberAddr)
        memberList = self.ms.distGetMembers(id)
        print memberList
        self.assertEquals(len(memberList), 1)

    def test_distDelMember(self):
        # Exception GroupwareNoSuchObject
        # distDelMember(self, id, address):
        id = self.distListName
        memberAddr = self.__primaryEmailAddress_A
        self.ms.distAdd(id, "DIST" + self.__primaryEmailAddress_A)
        
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distDelMember, id, "hape@exdom.intranet.gonicus.de")
        self.ms.distAddMember(id, memberAddr)

        self.assertTrue(self.ms.distDelMember(id, memberAddr))
         

    def test_distSetMailLimit(self):
        # Exception GroupwareNoSuchObject
        # distSetMailLimit(self, id, receive=None):
        id = self.distListName
        # exception for non existent distList
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distSetMailLimit, id)

        self.ms.distAdd(id, "DIST" + self.__primaryEmailAddress_A)
        
        self.assertTrue(self.ms.distSetMailLimit(id, 1234))

    def test_distGetMailLimit(self):
        # Exception GroupwareNoSuchObject
        # distGetMailLimit(self, id):
        id = self.distListName
        # exception for non existent distList
        self.assertRaises(GroupwareNoSuchObject, 
            self.ms.distGetMailLimit, id)
        self.ms.distAdd(id, "DIST" + self.__primaryEmailAddress_A)

        #what is the initial state?
        #self.assertEquals(self.ms.distGetMailLimit(id), None)

        mylimit = 12345
        self.ms.distSetMailLimit(id, mylimit)
        self.assertEquals(self.ms.distGetMailLimit(id)["receive"], mylimit)

if __name__ == '__main__':
    unittest.main()

