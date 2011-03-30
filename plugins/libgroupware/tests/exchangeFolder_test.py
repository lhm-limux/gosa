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

class TestExchangeFolderFunctions(unittest.TestCase):

    ExchangeTimeout = 60
    testuserA = "Atest" + win32api.GetUserName() + "A"
    testuserB = "Atest" + win32api.GetUserName() + "B"

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
        # Nothing to be done here - moved to class startup.

    def tearDown(self):
        """ Run after every test """
        try:
            self.ms.acctDel(self.__defaultUserId_B)
        except:
            pass
        try:
            self.ms._deleteMapiProfile(self.__defaultUserId_A)
        except:
            pass
    def test_folderAddPublicFolder(self):
        # Exception GroupwareNoSuchObject2
        newFolderId = "shared/All Public Folders/Wumperichinge"
        self.assertTrue(self.ms.folderAdd(newFolderId))

        newSubFolderId = "shared/All Public Folders/Wumperichinge/second"
        self.assertTrue(self.ms.folderAdd(newSubFolderId))

        #cleanup
        try:
            self.ms.folderDel(newFolderId)
        except:
            pass

    def test_folderAdd(self):
        # Exception GroupwareNoSuchObject2
        newFolderId = "user/"+self.testuserA+"/Wumperichinge"
        self.assertTrue(self.ms.folderAdd(newFolderId))

        newSubFolderId = "user/"+self.testuserA+"/Wumperichinge/second"
        self.assertTrue(self.ms.folderAdd(newSubFolderId))

        #cleanup
        try:
            self.ms.folderDel(newFolderId)
        except:
            pass

    
    def test_folderExists(self):
        newFolderId = "user/"+self.testuserA+"/Wumperiching"
        # not existing yet
        self.assertFalse(self.ms.folderExists(newFolderId))

        self.ms.folderAdd(newFolderId)
        # should exist now
        self.assertTrue(self.ms.folderExists(newFolderId))
        #cleanup
        self.ms.folderDel(newFolderId)
        
    def test_folderListForUser(self):
        myFolder = self.ms.folderList("user/wiwu/")
        self.assertTrue(len(myFolder)>0)

    def test_folderList(self):
        # Exception GroupwareNoSuchObject
        newFolderId = "user/"+self.testuserA+"/base"
        newFolderIdSub = "user/"+self.testuserA+"/base/sub"
        
        #newFolderId = "user/"+self.testuserA+"/Inbox/base"
        #newFolderIdSub = "user/"+self.testuserA+"/Inbox/base/sub"
        # get all public folders using paramete=null
        sharedFolders = self.ms.folderList()
        #self.assertTrue(len(sharedFolders) > 0)
        
        # exception when folder does not exist
        currentFolders = self.ms.folderList(newFolderId)
        #self.assertEquals(len(currentFolders), 0)

        # empty list if it is empty
        self.ms.folderAdd(newFolderId)
        #self.assertEquals(len(self.ms.folderList(newFolderId)), 1)

        #some other folder inside
        self.ms.folderAdd(newFolderIdSub)
        currentFolders = self.ms.folderList(newFolderId)
        #self.assertEquals(len(currentFolders), 2)
        self.ms.folderDel(newFolderId)

    def test_folderDel(self):
        # Exception GroupwareNoSuchObject
        # folderDel(self, id):
        notExistingFolder = "user/"+self.testuserA+"/Notexisting"
        newFolderId = "user/"+self.testuserA+"/Wumperich"
        newSubFolderId = "user/"+self.testuserA+"/Wumperich/second"

        
        self.assertRaises(GroupwareValueError, self.ms.folderDel,
            notExistingFolder)

        try:
            self.ms.folderAdd(newFolderId)
        except:
            pass
        self.assertTrue(self.ms.folderDel(newFolderId)) 
    """
    def test_folderSetAndGetMembers(self):
        notExistingFolder = "user/"+self.testuserA+"/Posteingang/Notexisting"
        folderId = "user/"+self.testuserA+"/Postausgang/Wumperich"
        #newSubFolderId = "user/"+self.testuserA+"/Posteingang/"

        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareValueError, \
            self.ms.folderGetMembers, notExistingFolder)

        self.ms.acctAdd(self.testuserB, self.testuserB + "@exdom.intranet.gonicus.de")
        self.ms.folderAdd(folderId)        
        # Exception GroupwareNoSuchObject
        # folderSetMembers(self, id, members):
        memberDict = {self.testuserB: RIGHTS_WRITE}
        self.assertRaises(GroupwareValueError, \
            self.ms.folderSetMembers, notExistingFolder, memberDict)

        self.assertTrue(self.ms.folderSetMembers( \
            folderId, memberDict))

        members = self.ms.folderGetMembers(folderId)
        print members
        self.assertTrue(len(members) == 2, "Count of members should be (2) testuser plus standard but is ("+str(len(members))+")")
    """        
    def test_sharedFolderMember(self):
        notExistingFolder = "shared/All Public Folders/Notexisting"
        folderId = "shared/All Public Folders/testordner"

        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareValueError, \
            self.ms.folderGetMembers, notExistingFolder)

        members = self.ms.folderGetMembers(folderId)
        print members
        self.assertTrue(len(members) == 2, "Count of members should be (2) testuser plus standard but is ("+str(len(members))+")")
        
        self.ms.folderSetMembers(folderId, members)
    
    def test_folderAddMember(self):
        #init strings.
        nonExmemberId = "GiselaHartmann"
        memberId = self.testuserB
        memberRechte = RIGHTS_READ
        
        #expect an Exception for non existent Folders
        # Exception GroupwareNoSuchObject
        # Example: folderAddMember(self, id, account_id, permission):
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.folderAddMember, nonExmemberId, memberId, memberRechte)

         #add a Folder to test
        testFolderId = "user/"+self.testuserA+"/Posteingang"
        #self.ms.folderAdd(testFolderId)
        self.ms.acctAdd(self.testuserB, self.testuserB + "@exdom.intranet.gonicus.de")
        for i in range(0, 60):
            if self.ms.acctGetStatus(self.testuserB)['status'] != PENDING:
                break
            sleep(1)
        else:
            raise GroupwareTimeout("the creating testuserA has thrown a timeout after 60 seconds.")
        
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.folderAddMember, testFolderId, nonExmemberId, memberRechte)

        #try to ad a member and check for Success
        self.assertTrue(self.ms.folderAddMember(testFolderId, memberId, \
            memberRechte))
            
        members = self.ms.folderGetMembers(testFolderId)
        print members
        self.assertTrue(members[memberId] == RIGHTS_READ )

        testFolderId = "shared/All Public Folders/testordner"
        print "Start test for " , testFolderId
        self.assertTrue(self.ms.folderAddMember(testFolderId, memberId, \
            memberRechte))
            
        members = self.ms.folderGetMembers(testFolderId)
        print members
        self.assertTrue(members[memberId] == RIGHTS_READ )

        self.ms.acctDel(self.testuserB)


    def test_folderDelMember(self):
        #self.fail("test_folderDelMember - not yet tested (implemented?)")
        
        # folder of testuserA which will get its acls changed
        testFolderId = "user/"+self.testuserA+"/Posteingang"
        # memberId of testuserB who will get permissions on the folder above 
        # and who will be stripped of all permissions aftewards
        memberId =  self.__defaultUserId_B
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.folderDelMember, testFolderId, memberId)

        self.ms.acctAdd(self.__defaultUserId_B, self.__primaryEmailAddress_B)
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.folderDelMember, testFolderId + "/nonExistentFolder", memberId)

        memberRechte = RIGHTS_READ
        self.assertTrue(self.ms.folderAddMember(testFolderId, memberId, memberRechte))
        self.assertTrue(self.ms.folderDelMember(testFolderId, self.__defaultUserId_B))

        self.ms.acctDel(self.__defaultUserId_B)

    def test_folderListWithMembers(self):
        profileName = self.__defaultUserId_A
        compFolders = self.ms.folderListWithMembers("user/" + profileName)
        #Do some assurances here

    def helper_AddTestUserA(me, self):
        pass

    def helper_AddTestUserB(self):
        self.ms.acctAdd(self.__defaultUserId_B, self.__primaryEmailAddress_B, \
            self.__defaultLocation, self.__defaultRDN)
        self.__defaultUserSet_B = True

if __name__ == '__main__':
    unittest.main()
