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

        cls.__primaryEmailAddress_A = \
            cls.testuserA + "@exdom.intranet.gonicus.de"
        cls.__emailAddress_A =  \
            cls.testuserA + "GosaMailtestsA.second@gonicus.de"
        cls.__propertie_A = "propA"
        cls.__defaultUserSet_A = False

        #==================================================
        # credentials for test user B
        #==================================================
        cls.__defaultUserId_B = cls.testuserB
        cls.__defaultAddress_B = "testStrassenB"
        cls.__primaryEmailAddress_B = \
            cls.testuserB + "exdom.intranet.gonicus.de"
        cls.__emailAddress_B = \
            cls.testuserA + "GosaMailtestsA.second@gonicus.de"
        cls.__propertie_B = "propB"
        cls.__primaryEmailAddress_B = "gosaExchangetestB@gonicus.de"
        cls.__defaultUserSet_B = False

        try:
            cls.ms.acctAdd(cls.__defaultUserId_A, cls.__primaryEmailAddress_A)
        except:
            cls.ms.acctDel(cls.__defaultUserId_A)
            cls.ms.acctAdd(cls.__defaultUserId_A, cls.__primaryEmailAddress_A)

        #checking the status of the account creation process.
        cls.__defaultUserSet_A = True
        for i in range(0, 60):
            if cls.ms.acctGetStatus(\
                cls.__defaultUserId_A)['status'] != PENDING:
                break
            sleep(1)
        else:
            raise GroupwareTimeout(\
                "the creating testuserA has thrown a timeout after 60 seconds.")
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

    def test_acctSetQuota(self):
        #testig some casting functinality - just to be personally sure.
        try:
            CastTest = int("234")
            CastTest = int(125)
            CastTest = int(1.5)
            CastTest = int(0.5)
        except Exception:
            self.fail("Casting to int went wrong", e)

        try:
            int("nText")
        except ValueError:
            pass
        except:
            self.fail("Casting to int went wron", e)

        # acctSetQuota(self, id, warn_limit, send_limit, hard_limit, hold):
        wLimit = 1000
        sLimit = 2000
        hLimit = 2500
        hold = 14
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctSetQuota,
            self.__defaultUserId_B, wLimit, sLimit, hLimit, hold)
        self.assertTrue(self.ms.acctSetQuota(
            self.__defaultUserId_A, wLimit, sLimit, hLimit, hold))

    # This function throws errors!!
    def test_acctGetQuota(self):
        # Exception GroupwareNoSuchObject
        # acctGetQuota(self, id):
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctGetQuota, self.__defaultUserId_B)
        wLimit = 1001
        sLimit = None
        hLimit = None
        hold = None

        self.ms.acctSetQuota(self.__defaultUserId_A,
            wLimit, sLimit, hLimit, hold)

        dictData = self.ms.acctGetQuota(self.__defaultUserId_A)
        self.assertEquals(dictData["warn_limit"], wLimit)
        self.assertEquals(dictData["send_limit"], 0)
        self.assertEquals(dictData["hard_limit"], 0)
        #self.assertEquals(dictData["hold"], hold)
        self.assertEquals(dictData["usage"], 0)

        wLimit = 1001
        sLimit = None 
        hLimit = 2000 
        hold = None

        self.ms.acctSetQuota(self.__defaultUserId_A,
        wLimit, sLimit, hLimit, hold)

        dictData = self.ms.acctGetQuota(self.__defaultUserId_A)
        self.assertEquals(dictData["warn_limit"], wLimit)
        self.assertEquals(dictData["send_limit"], 0)
        self.assertEquals(dictData["hard_limit"], hLimit)
        #self.assertEquals(dictData["hold"], hold)
        self.assertEquals(dictData["usage"], 0)
        
        wLimit = None
        sLimit = 1024
        hLimit = 0
        hold = None

        self.ms.acctSetQuota(self.__defaultUserId_A,
        wLimit, sLimit, hLimit, hold)

        dictData = self.ms.acctGetQuota(self.__defaultUserId_A)
        self.assertEquals(dictData["warn_limit"], 0)
        self.assertEquals(dictData["send_limit"], sLimit)
        self.assertEquals(dictData["hard_limit"], hLimit)
        #self.assertEquals(dictData["hold"], hold)
        self.assertEquals(dictData["usage"], 0)


    def test_acctSetPrimaryMailAddress(self):
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject,
            self.ms.acctSetPrimaryMailAddress, self.__defaultUserId_B, \
            self.__emailAddress_B)

        self.assertRaises(GroupwareValueError, self.ms.acctSetPrimaryMailAddress, \
                self.__defaultUserId_A, "someEmail")
        #TODO: The Exchangeserver seems to be asynchronus - the result is that a brand new user
        #is not immediately available for changes - this must be delt with later.
        self.ms.acctSetPrimaryMailAddress(self.__defaultUserId_A, self.__emailAddress_A)

    def test_acctGetPrimaryMailAddress(self):
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctGetPrimaryMailAddress, self.__defaultUserId_B)

        #resetting the former primary Mail.
        self.ms.acctSetPrimaryMailAddress(self.__defaultUserId_A, self.__primaryEmailAddress_A)
        # Assert getting a primary Address
        #self.ms.acctSetPrimaryMailAddress(self.__defaultUserId_A, \
        #    self.__primaryEmailAddress_A)
        pMail = self.ms.acctGetPrimaryMailAddress(self.__defaultUserId_A)
        self.assertEquals(self.__primaryEmailAddress_A, pMail)

        #except Exception:
        #    traceback.print_exc()
        #    self.fail("Could not create default user B in the \
        #    alternative Realm - heck the traceback above.")

    def test_acctExists(self):
        self.assertFalse(self.ms.acctExists(self.__defaultUserId_B))
        self.assertTrue(self.ms.acctExists(self.__defaultUserId_A))

    def testGetMailboxLocations(self):
        mailboxlist = self.ms.getMailboxLocations()
        self.assertTrue(len(mailboxlist) > 0)

#    #MAPI function are not yet successful
    def test_acctSetOutOfOfficeReply(self):
        # Eexception GroupwareNoSuchObject
        # acctSetOutOfOfficeReply(self, id, msg, begin=None, end=None):
        ooMess = "i am out of office, sorry"

        #24*60*60 = 86400
        now = time()
        yesterday = now - 86400
        tomorrow = now + 86400

        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctSetOutOfOfficeReply,\
            self.__defaultUserId_B, ooMess, yesterday, tomorrow)

        # wrong order of params

        #self.assertRaises(GroupwareValueError, self.ms.acctSetOutOfOfficeReply, \
        #    self.__defaultUserId_A, ooMess, None, None)

        self.assertTrue(self.ms.acctSetOutOfOfficeReply( \
                self.__defaultUserId_A, ooMess, yesterday, tomorrow))

        #self.assertRaises(GroupwareValueError, self.ms.acctSetOutOfOfficeReply,\
        #    self.__defaultUserId_A, ooMess, tomorrow, yesterday)

    def test_acctGetOutOfOfficeReply(self):
        # Exception GroupwareNoSuchObject
#        self.assertRaises(GroupwareNoSuchObject, \
#        self.ms.acctGetOutOfOfficeReply, self.__defaultUserId_A)
        inputmsg = "I am away, sorry"
        self.ms.acctSetOutOfOfficeReply(self.__defaultUserId_A, \
        inputmsg, 123456789, 987654321)

        msg = self.ms.acctGetOutOfOfficeReply(self.__defaultUserId_A)
        self.assertEquals(inputmsg, msg["message"])

    def test_acctRemoveOutOfOfficeReply(self):
        # Exception GroupwareNoSuchObject
        #        self.assertRaises(GroupwareNoSuchObject, \
        #        self.ms.acctGetOutOfOfficeReply, self.__defaultUserId_A)
        inputmsg = "I am away, sorry"
        self.ms.acctSetOutOfOfficeReply(self.__defaultUserId_A, \
            inputmsg, 123456789, 987654321)

        self.assertTrue(self.ms.acctSetOutOfOfficeReply(self.__defaultUserId_A))

        self.assertFalse( self.ms.acctGetOutOfOfficeReply(self.__defaultUserId_A))


    def test_acctGetLocation(self):
        #acctGetLocation(self, id):
        self.ms.acctGetLocation(self.__defaultUserId_A)

    def test_acctList(self):
        # GroupwareNoSuchObject must be throw on empty exchange server
        # cannot simulate empty Groupware server!
        #self.assertRaises(GroupwareNoSuchObject, self.ms.acctList)

        # Confirm list has UserA
        list = self.ms.acctList()
        self.assertTrue(len(list) > 1)

        foundA = False
        for entry in list:
            if entry == self.__defaultUserId_A:
                foundA = True
        self.assertTrue(foundA)

        """
        don't test alternate RDB
        """
#        # Add default user B to alternativeRDB and test
#        #self.ms.acctAdd(self.__defaultUserId_B, self.__primaryEmailAddress_B, \
#        #    self.__defaultLocation, self.__alternativeRDN)
#
#        list = self.ms.acctList(self.__alternativeRDN)
#         Confirm list has UserA and B
#        foundA = False
#        foundB = False
#        for entry in list:
#            if entry  == self.__defaultUserId_A:
#                foundA = True
#            if entry  == self.__defaultUserId_B:
#                foundB = True
#        self.assertFalse(foundA)
#        self.assertTrue(foundB)
#        removing the test user again to tidy the AD up
#        #self.ms.acctDel(self.__defaultUserId_B, self.__alternativeRDN)

    def test_acctAddAlternateMailAddress(self):
        # Eexception GroupwareNoSuchObject
        # acctAddAlternateMailAddress(self, id, address)

        aAddress = "additionalAddress@gonicus.de"
        self.assertRaises(GroupwareNoSuchObject, self.ms.\
            acctAddAlternateMailAddress, self.__defaultUserId_B, \
            aAddress)
        self.assertTrue(self.ms.acctAddAlternateMailAddress(\
            self.__defaultUserId_A, aAddress))
        self.ms.acctDelAlternateMailAddress(self.__defaultUserId_A, aAddress)

    def test_acctSetAlternateMailAddresses(self):
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctSetAlternateMailAddresses, \
            self.__defaultUserId_B, ["someAddress@gonicus.de"])

        self.assertRaises(GroupwareValueError, \
            self.ms.acctSetAlternateMailAddresses, \
            self.__defaultUserId_A, ["someInvalidEmail.de"])

        mailList = ["mailA@gonicus.de", "mailB@gonicus.de"]

        self.assertTrue(self.ms.acctSetAlternateMailAddresses(\
                self.__defaultUserId_A, mailList))

        # Check the alternateAddresse contain the new address.
        addrList = self.ms.acctGetAlternateMailAddresses(self.__defaultUserId_A)
        self.assertEquals(len(addrList), 2)

        # Deleting the addresses by
        self.assertTrue(self.ms.acctSetAlternateMailAddresses(\
                self.__defaultUserId_A, mailList))

        # check the deletion.
        addrList = self.ms.acctGetAlternateMailAddresses(
            self.__defaultUserId_A)
        self.assertEquals(len(addrList), 0)

    def test_acctGetAlternateMailAddresses(self):
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject, self.ms.\
            acctGetAlternateMailAddresses, self.__defaultUserId_B)

        self.ms.acctSetAlternateMailAddresses(self.__defaultUserId_A, \
            ["mailA@gonicus.de", "mailB@gonicus.de"])

        addrList = self.ms.acctGetAlternateMailAddresses(self.__defaultUserId_A)
        self.assertEquals(addrList.count("mailA@gonicus.de"), 1)

    def test_acctDelAlternateMailAddress(self):
        # Exception GroupwareNoSuchObject
        self.assertRaises(GroupwareNoSuchObject, self.ms.\
            acctDelAlternateMailAddress, self.__defaultUserId_B, \
            "unknown@gonicus.de")

        aAddress = "additionalAddress@gonicus.de"
        self.ms.acctAddAlternateMailAddress(self.__defaultUserId_A, aAddress)

        self.assertTrue(self.ms.acctDelAlternateMailAddress(\
            self.__defaultUserId_A, aAddress))

        addrList = self.ms.acctGetAlternateMailAddresses(\
                self.__defaultUserId_A)
        self.assertEquals(addrList.count(aAddress), 0)

    def test_acctAddMailForwardAddress(self):

        # TODO:
        # remove the address hape@exdom.intranet.gonicus.de which has got to be in exchange for this test.
        # Exception GroupwareNoSuchObject
        forwMail = "newfMail@gonicus.de"

        # TODO:
        # find out which exceptions get thrown here
        self.assertRaises(Exception, self.ms.acctAddMailForwardAddress, \
            self.__defaultUserId_A, forwMail)

        # TODO:
        # cycle de1tection - the following line should cause a cycle forwarding.
        # self.assertTrue(1self.ms.acctAddMailForwardAddress(self.__defaultUserId_A, self.__primaryEmailAddress_A,  True ));
        self.assertTrue(self.ms.acctAddMailForwardAddress(self.__defaultUserId_A,
            "hape@exdom.intranet.gonicus.de",  True))
        # remove the forward address
        self.ms.acctDelMailForwardAddress(self.__defaultUserId_A, "hape@exdom.intranet.gonicus.de")

    def test_acctSetMailForwardAddresses(self):

        # TODO:
        # remove the address hape@exdom.intranet.gonicus.de which has got to be in exchange for this test.

        # Exception GroupwareNoSuchObject
        mailList = ["mailA@gonicus.de", "mailB@gonicus.de"]
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctSetMailForwardAddresses, \
            self.__defaultUserId_B, {self.__primaryEmailAddress_A: True})

        # wrong list of mail addreses
        self.assertRaises(GroupwareValueError, self.ms.acctSetMailForwardAddresses, \
            self.__defaultUserId_A, mailList)

        # correct but too many
        mailList = {self.__primaryEmailAddress_A: True,  "hape@exdom.intranet.gonicus.de": True}
        self.assertRaises(GroupwareValueError, self.ms.acctSetMailForwardAddresses, \
            self.__defaultUserId_A, mailList)

        #Add one address successfully.
        self.assertTrue(self.ms.acctSetMailForwardAddresses(self.__defaultUserId_A, 
            {self.__primaryEmailAddress_A: True}))
        # delete by setting an empty array
        self.assertTrue(self.ms.acctSetMailForwardAddresses(self.__defaultUserId_A, {}))

        fMail = self.ms.acctGetMailForwardAddresses(self.__defaultUserId_A)

        self.assertEquals(len(fMail), 0)
        # remove the forward address
        # do not use del function just pass an empty Array
        #self.ms.acctDelMailForwardAddress(self.__defaultUserId_A, "hape@exdom.intranet.gonicus.de")

    def test_acctGetMailForwardAddresses(self):
        # TODO:
        # remove the address hape@exdom.intranet.gonicus.de which has got to be in exchange for this test.

        # Exception GroupwareNoSuchObject
        self.assertRaises(Exception,  self.ms.acctGetMailForwardAddresses, \
                self.__defaultUserId_B)

        self.ms.acctAddMailForwardAddress(self.__defaultUserId_A, self.__primaryEmailAddress_A, True)
        listForwMails = self.ms.acctGetMailForwardAddresses(self.__defaultUserId_A)

        self.assertEquals(len(listForwMails), 1)

    def test_acctDelMailForwardAddress(self):
        # Exception GroupwareNoSuchObject
        noMail = "nonExistent@gonicus.de"
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctDelMailForwardAddress, 
            self.__defaultUserId_B, self.__primaryEmailAddress_A)

        self.assertRaises(GroupwareValueError, self.ms.acctDelMailForwardAddress, 
            self.__defaultUserId_A, noMail)

        self.ms.acctAddMailForwardAddress(self.__defaultUserId_A, 
            "hape@exdom.intranet.gonicus.de", True)

        self.assertTrue(self.ms.acctDelMailForwardAddress(self.__defaultUserId_A, \
            "hape@exdom.intranet.gonicus.de"))

#    def test_acctSetProperties(self):
#        # Exception GroupwareNoSuchObject
#        # acctSetProperties(self, id, props):
#        dummyPros = "SMTP/SMTPS/IMAP/IMAPS/POP/POPS"
#        self.assertRaises(GroupwareNoSuchObject, \
#            self.ms.acctSetProperties, self.__defaultUserId_A, dummyPros)
#        self.helper_AddTestUserA()
#
#        try:
#            self.assertTrue(self.ms.acctSetProperties(self, \
#                self.__defaultUserId_A, dummyPros))
#        except (Exception), e:
#            self.fail("Exception while setting propertie" + e)
#
#    def test_acctGetProperties(self):
#        # Exception GroupwareNoSuchObject
#        # acctGetProperties(self, id):
#        dummyPros = "SMTP/SMTPS/IMAP/IMAPS/POP/POPS"
#        self.assertRaises(GroupwareNoSuchObject, \
#            self.ms.acctGetProperties, self.__defaultUserId_A)
#        self.helper_AddTestUserA()
#        self.ms.acctSetProperties(self.__defaultUserId_A, dummyPros)
#
#        try:
#            self.assertEquals(dummyPros, self.ms.acctGetProperties(\
#                self, self.__defaultUserId_A))
#        except (Exception), e:
#            self.fail("Exception while getting propertie" + e)
#

    def test_acctSetMailLimit(self):
        # Exception GroupwareNoSuchObject
        # acctSetMailLimit(self, id, send=None, receive=None)
        send = 100
        receive = 101

        self.assertTrue(self.ms.acctSetMailLimit(
            self.__defaultUserId_A, send, receive))

    def test_acctGetMailLimit(self):
        # Exception GroupwareNoSuchObject
        # acctGetMailLimit(self, id):
        send = 100
        receive = 101
        self.ms.acctSetMailLimit(self.__defaultUserId_A, send, receive)

        dictData = self.ms.acctGetMailLimit(self.__defaultUserId_A)
        self.assertEquals(dictData['send'], send)
        self.assertEquals(dictData['receive'], receive)

    def test_acctSetFilters(self):
        # Exception GroupwareNoSuchObject
        # acctSetFilters(self, id, data):
        filterOne = {'name': 'Rule1', "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", 'VALUE': \
                "oil spill"}], 'actions': [{'action': 'delete'}]}
        filterTwo = {'name': 'Rule2', "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", 'VALUE': \
                "kachelmann"}], 'actions': [{'action': 'delete'}]}


        filterlist = (filterOne, filterTwo)
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctSetFilters, self.testuserB, filterlist)

        self.assertTrue(GroupwareNoSuchObject, \
            self.ms.acctSetFilters( \
                self.__defaultUserId_A, filterlist))

    def test_acctGetFilters(self):
        # Exception GroupwareNoSuchObject
        # acctGetFilters(self, id):
        newFolderId = "user/"+self.testuserA+"/Wumperichinge"
        newFolderId2 = "user/"+self.testuserA+"/Wumperichinge/Testerfeld"
        sharedFolderId = "shared/All Public Folders/testordner"
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctGetFilters, self.testuserB)
        filterOne = {\
            'name': "Filter1",
            "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", \
                'VALUE': "oil spill"}], 'actions': [{'action': 'delete'}]}
        filterTwo = {\
            'name': "Filter2",
            "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", \
            'VALUE': "kachelmann"}],  \
            'actions': [{'action': 'reply', 'value': 'this is a message'}]}
        filterThree = {'name': 'Rule3',"TYPE": "AND", \
            "CONDITIONS" : [{'FIELD': 'date', \
            'COMPARATOR': 'less than', 'VALUE': 1287996340}], \
            'actions': [ \
                    {'action': 'copy to', 'value': newFolderId}, \
                    ] }

        filterFour = {'name': 'Rule4',"TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", 'VALUE': \
                "kachelmann"}], 'actions': [ \
                    {'action': 'move to', 'value': sharedFolderId}, \
                    {'action': 'mark as', 'value': 'read'} ] }
        filterFive = {'name': 'Rule3',"TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", 'VALUE': \
                "kachelmann"}], 'actions': [ \
                    {'action': 'copy to', 'value': newFolderId2}, \
                    ] }

        filterlist = (filterOne, filterTwo, filterThree, filterFour, \
            filterFive)

        self.assertTrue(self.ms.folderAdd(newFolderId))
        self.assertTrue(self.ms.folderAdd(newFolderId2))
        
        self.ms.acctSetFilters(self.__defaultUserId_A, filterlist)

        filtersList = self.ms.acctGetFilters(self.__defaultUserId_A)
        #sampling only
        self.assertEquals(filtersList[0]["TYPE"], filterOne["TYPE"])
        self.assertTrue(filtersList[0]["id"] != None, "Missing Unique ID")
        self.assertEquals(filtersList[0]["actions"], \
            filterOne["actions"])
        self.assertEquals(filtersList[0]["CONDITIONS"], \
            filterOne["CONDITIONS"])
        self.assertEquals(filtersList[1]["actions"], \
            filterTwo["actions"])
        self.assertEquals(filtersList[2]["actions"], \
            filterThree["actions"])
        self.assertEquals(filtersList[3]["actions"], \
            filterFour["actions"])
        self.assertEquals(filtersList[4]["actions"], \
            filterFive["actions"])

    def test_acctAddFilter(self):
        # Exception GroupwareNoSuchObject
        # acctAddFilter(self, id, filter):
        filterOne = {'name': 'foo', "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", \
            'VALUE': "oil spill"}], \
            'actions': [{'action': 'delete'}]}
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctAddFilter, \
            self.testuserB, filterOne)

        self.ms.acctAddFilter(self.__defaultUserId_A, filterOne)

    def test_acctDelFilter(self):
        # Exception GroupwareNoSuchObject
        # acctDelFilter(self, id, filter_id):
        filterId = 0
        self.assertRaises(GroupwareNoSuchObject, \
            self.ms.acctDelFilter, self.testuserB, filterId)
        filterOne = {\
            "TYPE": "AND", \
            'CONDITIONS': [{'FIELD': "body", 'COMPARATOR': "is", \
            'VALUE': "oil spill"}], \
             'actions': [{'action': 'delete'}],
            'name': 'aFilter'}
        self.ms.acctSetFilters(self.__defaultUserId_A, [filterOne])

        filter = self.ms.acctGetFilters(self.__defaultUserId_A)

        self.assertTrue(len(filter) == 1,  \
            "Filter length should be 1 just the added Filter, but was " + str(len(filter)))
        filterId = filter[0]['id']

        # Test the  resulting set - should be empty
        filter = self.ms.acctDelFilter(self.__defaultUserId_A, filterId)
        self.assertTrue(filter)
        filter = self.ms.acctGetFilters(self.__defaultUserId_A)
        self.assertTrue(len(filter) == 0,  \
            "Filter length should be 0 just the added Filter, but was " + str(len(filter)))

    def test_mailAddressExists(self):
        # mailAddressExists(self, address):
        self.assertFalse(self.ms.mailAddressExists(self.__primaryEmailAddress_B))
        self.ms.acctSetPrimaryMailAddress(self.__defaultUserId_A, self.__primaryEmailAddress_A)
        self.assertTrue(self.ms.mailAddressExists(self.__primaryEmailAddress_A))

    def test_acctSetLocation(self):
        existingLocation = "someLocation"
        nonExistingLocation = "wrongLocation"
 
        #acctSetLocation(self, id, location) - id= unique account id
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctSetLocation,
            self.__defaultUserId_A, nonExistingLocation)
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctSetLocation,
            self.__defaultUserId_A, existingLocation)
        self.assertRaises(GroupwareNoSuchObject, self.ms.acctSetLocation,
            self.__defaultUserId_A, nonExistingLocation)
        self.ms.acctSetLocation(self.__defaultUserId_A, existingLocation)

    def test_acctAdd_Exceptions(self):
        
        # Try to add Account
        self.assertRaises(GroupwareObjectAlreadyExists, self.ms.acctAdd, self.__defaultUserId_A, \
            self.__primaryEmailAddress_A)
    
#     def test_acctAdd(self):
#        #=====================================================
#        # not covered by this test:
#        # GroupwareValueError will be throw if there is not
#        # distinct privateMDB
#        # this will not be tested because of the comlexity of this task
#        #=====================================================
#
#        #interface for the method to be tested.
#        #acctAdd(self, id, address, location=None, rdn=None):
#        self.__defaultRDN = "cn=Users"
#        self.__alternativeRDN = "ou=Testeinheit"
#
#        # Try to add Account
#        self.assertRaises(GroupwareObjectAlreadyExists, \
#            self.ms.acctAdd, self.__defaultUserId_A, \
#            self.__primaryEmailAddress_A)
#
#        try:
#            self.ms.acctAdd(self.__defaultUserId_A, self.__primaryEmailAddress_A)
#            self.__defaultUserSet_A = True
#        #checking the status of the account creation process.
#        except GroupwareNoSuchObject:
#            self.fail("GroupwareNoSuchObject exception thrown")
#        for i in range(0, 60):
#            if self.ms.acctGetStatus(self.__defaultUserId_A)['status'] != PENDING:
#                break
#            sleep(1)
#        else:
#            self.fail("Could not create default user A \
#                A timeout occured.")
#
#        #Awaiting Exception when rdn =None
#        self.assertRaises(Exception, \
#            self.ms.acctAdd, self.__defaultUserId_A, \
#            self.__primaryEmailAddress_A, self.__defaultLocation, \
#                None)
#
#        # Adding the same user must throw exception - even with another rdn
#        self.assertRaises(GroupwareObjectAlreadyExists, \
#            self.ms.acctAdd, self.__defaultUserId_A, \
#            self.__primaryEmailAddress_A, self.__defaultLocation, \
#                self.__alternativeRDN)
#
#        #creating a user in an alternative rdn.
#        self.assertRaises(GroupwareNoSuchObject, self.ms.acctAdd, self.__defaultUserId_B, self.__primaryEmailAddress_B)
#        try:
#            self.ms.acctAdd(self.__defaultUserId_B, \
#                self.__primaryEmailAddress_B, \
#                self.__defaultLocation, self.__alternativeRDN)
#        except GroupwareNoSuchObject:
#            self.fail("GroupwareNoSuchObject exception thrown")
#        except Exception:
#            self.fail("Could not create default user B \
#                check the traceback above.")
#        finally:
#            try:
#                self.ms.acctDel(self.__defaultUserId_B)
#            except Exception:
#                #do nothing here.
#                print "removed userB from alternative RDN"
#
#    def test_acctDel(self):
#        # Exception GroupwareNoSuchObject
#        self.assertRaises(GroupwareNoSuchObject, \
#            self.ms.acctDel, self.__defaultUserId_B)
#        
#        self.ms.acctAdd(self.__defaultUserId_B, self.__primaryEmailAddress_B)
#        # The test to remove a user.
#        self.assertTrue(self.ms.acctDel(self.__defaultUserId_B))

    def test_MapiProfile(self):
        profileName = self.__defaultUserId_A
        #try:
        #    # deleting profile
        #    self.ms._deleteMapiProfile(profileName)
        #except Exception:
        #    pass
        self.assertFalse(self.ms._mapiProfileExists(profileName))
        # creating profile - user Profile"
        self.ms._createMapiProfile(profileName)
        self.assertTrue(self.ms._mapiProfileExists(profileName))

        # deleting profile
        self.ms._deleteMapiProfile(profileName)

    def test_folderListWithMembers(self):
        profileName = self.__defaultUserId_A
        compFolders = self.ms.folderListWithMembers(profileName)
        print(compFolders)
        #Do some assurances here
        self.fail("failing just to get the messages.")


    def test_ComprehensiveUser(self):
        """
        TODO: This test might be obsolete since it tests a function which is
        for speedup purpose only and might get obsolete in the future
        """

        profileName = self.__defaultUserId_A
        comp =  self.ms.acctGetComprehensiveUser(profileName)

        #Do some self.assureEquals tests here
        self.assureEquals(comp["primaryMail"], self.__primaryEmailAddress_A)

    def helper_AddTestUserA(me, self):
        pass

    def helper_AddTestUserB(self):
        self.ms.acctAdd(self.__defaultUserId_B, self.__primaryEmailAddress_B, \
            self.__defaultLocation, self.__defaultRDN)
        self.__defaultUserSet_B = True

if __name__ == '__main__':
    unittest.main()
