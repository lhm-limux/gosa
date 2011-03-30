# -*- coding: utf-8 -*-
from libgroupware.exchange.main import MapiActionFactory
from libgroupware.exchange.main import GosaActionFactory
from libgroupware.exchange.main import MapiRestrictionFactory
from libgroupware.exchange.main import MapiRestrictionReader
import libgroupware.base as base
import unittest
import time
from datetime import date, datetime, timedelta
from win32com.mapi import mapitags
from libgroupware.base import Groupware, GroupwareTimeout, GroupwareObjectAlreadyExists, \
    GroupwareNoSuchObject, GroupwareError, LOOKUP, READ, STATUS, WRITE, INSERT, POST, \
    CREATE, DELETE, ADMINISTRATE, RIGHTS_NONE, RIGHTS_READ, RIGHTS_POST, \
    RIGHTS_APPEND, RIGHTS_WRITE, RIGHTS_ALL, SMTP, SMTPS, IMAP, IMAPS, \
    POP, POPS, HTTP, ACTIVE, INACTIVE, PENDING, ERROR,\
    OP_MOVE, OP_COPY , OP_FORWARD, OP_MARKAS, OP_DELETE, OP_REPLY, \
    OP_OOOREPLY, GroupwareValueError
from libgroupware.exchange.mapirestrictionreader import MapiRestrictionReader
from libgroupware.exchange.mapirestrictionfactory import MapiRestrictionFactory
from libgroupware.exchange.gosaactionfactory import GosaActionFactory
from libgroupware.exchange.mapiactionfactory import MapiActionFactory


"""
from libgroupware.base import Groupware, GroupwareObjectAlreadyExists, \
    GroupwareNoSuchObject, GroupwareValueError, ACTIVE, INACTIVE, PENDING, \
    RIGHTS_READ, RIGHTS_WRITE, GroupwareTimeout
TODO: GroupwareObjectAlreadyExists check if this exceptions
      has got to be tested somewhere here, too
"""



class MapiSimplifierStub():
    def getFolderString(self, storeEntryId, folderEntryId):
        if storeEntryId != 1:
            raise Exception
        if folderEntryId != 2:
            raise Exception
        return 'user/atestuser/testfolder'
    
    def getFolder(self, folderString):
        if folderString != 'user/atestuser/testfolder':
            raise Exception
        return 1234, 5678
        
    def getMessageText(self, messageId):
        if messageId != 12345:
            raise Exception
        return 'MyOOOText'
    
    def createMessage(self, messageText):
        if messageText != 'this is a message':
            raise Exception
        return '1234567890'

    def getAddressList(self, adrlistEid):
        if adrlistEid != 12345:
            raise Exception
        return ['xxx@xxx.xx']

class TestMapiActionFactory(unittest.TestCase):

    mapiUtility = MapiSimplifierStub()

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
    def setUp(self):
        pass;

    def tearDown(self):
        pass

    def test_createDeleteAsMapi(self):
        deleteAction = {'action': 'delete'}
        params = MapiActionFactory.createDeleteAsMapi(deleteAction)
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 1)
        self.assertEquals(params["acttype"], 10)

    def test_createMoveAsMapi(self):
        filter = {"action": 'move to', "value" : 'user/atestuser/testfolder'}
        params = MapiActionFactory.createMoveAsMapi(filter, self.mapiUtility)
        self.assertTrue(len(params) == 3)
        self.assertEquals(params["acttype"], 1)
        self.assertEquals(params["storeEntryId"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["folderEntryId"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["storeEntryId"][1], 1234)
        self.assertEquals(params["folderEntryId"][1], 5678)

    def test_createCopyAsMapi(self) :       
        filter = {"action": 'copy to', "value" : 'user/atestuser/testfolder'}
        params = MapiActionFactory.createCopyAsMapi(filter, self.mapiUtility)
        self.assertTrue(len(params) == 3)
        self.assertEquals(params["acttype"], 2)
        self.assertEquals(params["storeEntryId"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["folderEntryId"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["storeEntryId"][1], 1234)
        self.assertEquals(params["folderEntryId"][1], 5678)
        

    def test_createReplyAsMapi(self) :       
        replyAction = {'action': 'reply', 'value': 'this is a message'}
        params = MapiActionFactory.createReplyAsMapi(replyAction, self.mapiUtility)
        self.assertTrue(params != None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params["acttype"], 3)
        self.assertEquals(params["message"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["message"][1], '1234567890')

    def test_createOofReplyAsMapi(self):
        replyAction = {'action': 'oooreply', 'value': 'this is a message'}
        params = MapiActionFactory.createOofReplyAsMapi(replyAction, self.mapiUtility)
        self.assertTrue(params != None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params["acttype"], 4)
        self.assertEquals(params["message"][0], mapitags.PR_ENTRYID)
        self.assertEquals(params["message"][1], '1234567890')

    def test_createDeferActionAsMapi(self):
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)

    def test_createBounceAsMapi(self):
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)

    def test_createForwardAsMapi(self):
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)
            
    def test_createTagAsMapi(self):
        #createMarkAsRead = None #{'action': 'delete'}
        #params = MapiActionFactory.createTagAsMapi(createMarkAsRead)
        #self.assertTrue(params is not None, "Shouldn't return None")
        #self.assertTrue(len(params) == 2)
        #self.assertEquals(params["acttype"], 9)
        #self.assertTrue(len(params["propTag"]) == 2)
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)
            
    def test_createMarkAsReadAsMapi(self):
        createMarkAsRead = {'action': base.OP_MARKAS, 'value': 'read'}
        params = MapiActionFactory.createMarkAsReadAsMapi(createMarkAsRead)
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 1)
        self.assertEquals(params["acttype"], 11)

        
class TestGosaActionFactory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
    def setUp(self):
        pass;

    def tearDown(self):
        pass

    def test_createMoveFromMapi(self):
        mapiUtility = MapiSimplifierStub()
        mapiReturn = {'acttype': 1, "actMoveCopy": {'storeEntryId': 1, 'fldEntryId': 2}}
        param = GosaActionFactory.createMoveFromMapi(mapiReturn, mapiUtility)
        self.assertTrue(param is not None)
        self.assertTrue(len(param) == 2)
        self.assertEquals(param["action"], base.OP_MOVE)
        self.assertEquals(param["value"], 'user/atestuser/testfolder')

    def test_createCopyFromMapi(self):
        mapiUtility = MapiSimplifierStub()
        mapiReturn = {'acttype': 2, "actMoveCopy": {'storeEntryId': 1, 'fldEntryId': 2}}
        param = GosaActionFactory.createCopyFromMapi(mapiReturn, mapiUtility)
        self.assertTrue(param is not None)
        self.assertTrue(len(param) == 2)
        self.assertEquals(param["action"], base.OP_COPY)
        self.assertEquals(param["value"], 'user/atestuser/testfolder')

    def test_createReplyFromMapi(self):      
        mapiUtility = MapiSimplifierStub()
        mapiReturn = {'acttype': 3, "message": (mapitags.PR_ENTRYID, 12345)}
        param = GosaActionFactory.createReplyFromMapi(mapiReturn, mapiUtility)
        self.assertTrue(param is not None)
        self.assertTrue(len(param) == 2)
        self.assertEquals(param["action"], base.OP_REPLY)
        self.assertEquals(param["value"], 'MyOOOText')


    def test_createOofReplyFromMapi(self):
        mapiUtility = MapiSimplifierStub()
        mapiReturn = {'acttype': 3, "message": (mapitags.PR_ENTRYID, 12345)}
        param = GosaActionFactory.createOofReplyFromMapi(mapiReturn, mapiUtility)
        self.assertTrue(param is not None)
        self.assertTrue(len(param) == 2)
        self.assertEquals(param["action"], base.OP_OOOREPLY)
        self.assertEquals(param["value"], 'MyOOOText')

    def test_createDeferActionFromMapi(self):
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)

    def test_createBounceFromMapi(self):
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)

    def test_createForwardFromMapi(self):
        mapiUtility = MapiSimplifierStub()
        mapiReturn = {'acttype': 7, "adrlist": (mapitags.PR_ENTRYID, 12345)}
        param = GosaActionFactory.createForwardFromMapi(mapiReturn, mapiUtility)
        self.assertTrue(param is not None)
        self.assertTrue(len(param) == 2)
        self.assertEquals(param["action"], base.OP_FORWARD)
        self.assertEquals(param["value"], ['xxx@xxx.xx'])

    def test_createTagFromMapi(self):
        #mapiUtility = MapiSimplifierStub()
        #mapiReturn = {'acttype': 8, "adrlist": (mapitags.PR_ENTRYID, 12345)}
        #param = GosaActionFactory.createTagFromMapi(mapiReturn, mapiUtility)
        #self.assertTrue(param is not None)
        #self.assertTrue(len(param) == 2)
        #self.assertEquals(param["action"], base.OP_MARKAS)
        #self.assertEquals(param["value"], ['xxx@xxx.xx'])
        self.assertRaises(NotImplementedError, \
            GosaActionFactory.createBounceFromMapi)
        
    def test_createDeleteFromMapi(self):
        mapiReturn = {'acttype': 10}
        gosaAction = GosaActionFactory.createDeleteFromMapi()
        self.assertTrue(gosaAction is not None)
        self.assertEquals(gosaAction['action'], 'delete')

    def test_createMarkAsReadFromMapi(self):
        mapiReturn = {'acttype': 11}
        gosaAction = GosaActionFactory.createMarkAsReadFromMapi()
        self.assertTrue(gosaAction is not None)
        self.assertEquals(gosaAction['action'], base.OP_MARKAS)
        self.assertEquals(gosaAction['value'], 'read')

class TestMapiRestrictionFactory(unittest.TestCase):

    mapiUtility = MapiSimplifierStub()

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
    def setUp(self):
        pass;

    def tearDown(self):
        pass

    def test_CreateEmptyRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : []}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], \
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(params[1], [])
        
    def test_CreateSingleEqualsContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'equal', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        # ignore case and fullstring
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))
        
    def test_CreateSingleEqualsNotContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'not equal', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x2) # NOT Restriction object
        self.assertEquals(len(res1[1]), 1)
        res1 = res1[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))

    def test_CreateSingleContaisContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'contains', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        # ignore cas - substring
        self.assertEquals(res2[0],0x00010001)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))

    def test_CreateSingleContainsNotContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'contains not', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x2) # NOT Restriction object
        self.assertEquals(len(res1[1]), 1)
        res1 = res1[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        # ignore cas - substring
        self.assertEquals(res2[0],0x00010001)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))


    def test_CreateSingleIsContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'is', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        #ignore case - fullstring
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))

    def test_CreateSingleIsNotContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'is not', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x2) # NOT Restriction object
        self.assertEquals(len(res1[1]), 1)
        res1 = res1[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        #ignore case - fullstring
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))


    def test_CreateSingleEmptyContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'is empty', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"],
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        # fullstring
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))

    def test_CreateSingleNotEmptyContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'is not empty', 'VALUE': 'tester'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"],
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x2) # NOT Restriction object
        self.assertEquals(len(res1[1]), 1)
        res1 = res1[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        # fullstring
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],0x0037001F)
        self.assertEquals(res2[2],(0x0037001F, 'tester'))

    def test_CreateDoubleAndContentRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'equal', 'VALUE': 'tester1'}, \
            {'FIELD': 'body', \
            'COMPARATOR': 'equal', 'VALUE': 'abodytext'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 2) # now two conditions
        # Test first condition
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],mapitags.PR_SUBJECT)
        self.assertEquals(res2[2],(mapitags.PR_SUBJECT, 'tester1'))
        self.assertEquals(res1[0], 0x3)
        # Test second condition
        res1 = params[1][1]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],mapitags.PR_BODY)
        self.assertEquals(res2[2],(mapitags.PR_BODY, 'abodytext'))
        self.assertEquals(res1[0], 0x3)

    def test_CreateDoubleOrContentRestriction(self):
        filter = {"TYPE": 'OR', "CONDITIONS" : [{'FIELD': 'subject', \
            'COMPARATOR': 'equal', 'VALUE': 'tester1'}, \
            {'FIELD': 'body', \
            'COMPARATOR': 'equal', 'VALUE': 'tester12323'}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x1)
        self.assertEquals(len(params[1]), 2) # now two conditions
        # Test first condition
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],mapitags.PR_SUBJECT)
        self.assertEquals(res2[2],(mapitags.PR_SUBJECT, 'tester1'))
        self.assertEquals(res1[0], 0x3)
        # Test second condition
        res1 = params[1][1]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x3)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00010000)
        self.assertEquals(res2[1],mapitags.PR_BODY)
        self.assertEquals(res2[2],(mapitags.PR_BODY, 'tester12323'))
        
    def test_CreateDateLTRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'date', \
            'COMPARATOR': 'less than', 'VALUE': 1287996340}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)

        params2 = params[1][0]
        self.assertEquals(len(params2), 2)
        self.assertEquals(params2[0], 0x0)
        self.assertEquals(len(params2[1]), 2)
        # Test date condition
        res1 = params2[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4) # PROPERTY CONDITION
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000002)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_DELIVERY_TIME)
        self.assertEquals(res2[2],(mapitags.PR_MESSAGE_DELIVERY_TIME, 0))

        # Test date condition
        res1 = params2[1][1]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4) # PROPERTY CONDITION
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000000)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_DELIVERY_TIME)
        self.assertEquals(res2[2], \
            (mapitags.PR_MESSAGE_DELIVERY_TIME, 1287996340))

    def test_CreateDateGTRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'date', \
            'COMPARATOR': 'greater than', 'VALUE': 1287996340}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)

        params2 = params[1][0]
        self.assertEquals(len(params2), 2)
        self.assertEquals(params2[0], 0x0)
        self.assertEquals(len(params2[1]), 2)
        # Test date condition
        res1 = params2[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4) # PROPERTY CONDITION
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000002)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_DELIVERY_TIME)
        self.assertEquals(res2[2],(mapitags.PR_MESSAGE_DELIVERY_TIME, 1287996340))

        # Test date condition
        res1 = params2[1][1]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4) # PROPERTY CONDITION
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000000)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_DELIVERY_TIME)
        self.assertEquals(res2[2], \
            (mapitags.PR_MESSAGE_DELIVERY_TIME, 2147483647))
            
    def test_CreateDateInvalidRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'date', \
            'COMPARATOR': 'is', 'VALUE': 1287996340}]}
        try:
            params = MapiRestrictionFactory.createRestriction(filter["TYPE"],  \
               filter['CONDITIONS'])
            self.fail("Should throw an GroupwareValueException")
        except GroupwareValueError:
            pass
            
    def test_CreateInvalidTypeRestriction(self):
        filter = {"TYPE": 'XOR', "CONDITIONS" : [{'FIELD': 'date', \
            'COMPARATOR': 'greater than', 'VALUE': 1287996340}]}
        try:
            params = MapiRestrictionFactory.createRestriction(filter["TYPE"],  \
               filter['CONDITIONS'])
            self.fail("Should throw an GroupwareValueException caused by XOR")
        except GroupwareValueError:
            pass
            
    def test_CreateSizeGTRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'size', \
            'COMPARATOR': 'greater than', 'VALUE': 2000}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000002)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_SIZE_EXTENDED)
        self.assertEquals(res2[2],(mapitags.PR_MESSAGE_SIZE_EXTENDED, 2000))

    def test_CreateSizeLTRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'size', \
            'COMPARATOR': 'less than', 'VALUE': 2002}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],0x00000000)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_SIZE_EXTENDED)
        self.assertEquals(res2[2],(mapitags.PR_MESSAGE_SIZE_EXTENDED, 2002))

    def test_CreateSizeISRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'size', \
            'COMPARATOR': 'is', 'VALUE': 2001}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],4)
        self.assertEquals(res2[1],mapitags.PR_MESSAGE_SIZE_EXTENDED)
        self.assertEquals(res2[2],(mapitags.PR_MESSAGE_SIZE_EXTENDED, 2001))

    #def test_CreateToEqualsRestriction(self):
    #    filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'to', \
    #        'COMPARATOR': 'is', 'VALUE': 'xxx@domain.org'}]}
    #    params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
    #        filter['CONDITIONS'])
    #    self.assertTrue(params is not None, "Shouldn't return None")
    #    self.assertTrue(len(params) == 2)
    #    self.assertEquals(params[0], 0x0)
    #    self.assertEquals(len(params[1]), 1)
    #    res1 = params[1][0]
    #    self.assertEquals(len(res1), 2)
    #    self.assertEquals(res1[0], 0x9)
    #    res2 = res1[1]
    #    self.assertEquals(len(res2), 3)
    #    self.assertEquals(res2[0],4)
    #    self.assertEquals(res2[1],mapitags.PR_MESSAGE_SIZE_EXTENDED)
    #    self.assertEquals(res2[2],(mapitags.PR_MESSAGE_SIZE_EXTENDED, 2001))

    def test_CreatePriorityISRestriction(self):
        filter = {"TYPE": 'AND', "CONDITIONS" : [{'FIELD': 'priority', \
            'COMPARATOR': 'is', 'VALUE': 2}]}
        params = MapiRestrictionFactory.createRestriction(filter["TYPE"], 
            filter['CONDITIONS'])
        self.assertTrue(params is not None, "Shouldn't return None")
        self.assertTrue(len(params) == 2)
        self.assertEquals(params[0], 0x0)
        self.assertEquals(len(params[1]), 1)
        res1 = params[1][0]
        self.assertEquals(len(res1), 2)
        self.assertEquals(res1[0], 0x4)
        res2 = res1[1]
        self.assertEquals(len(res2), 3)
        self.assertEquals(res2[0],4)
        self.assertEquals(res2[1],mapitags.PR_IMPORTANCE)
        self.assertEquals(res2[2],(mapitags.PR_IMPORTANCE, 2))

class TestMapiRestrictionFactory(unittest.TestCase):

    mapiUtility = MapiSimplifierStub()

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass
    def setUp(self):
        pass;

    def tearDown(self):
        pass

    def test_translateEmptyRestriction(self):
        restriction = []
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(comp, "AND")
        self.assertEquals(filter, [])

        restriction = [0x0, []]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(comp, "AND")
        self.assertEquals(filter, [])

    def test_translateSingleSubjectRestriction(self):
        restriction = [0x0, [(0x3, (0x00010000, 0x0037001F, (0x0037001F, 'tester')))]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "subject")
        self.assertEquals(element['COMPARATOR'], "is")
        self.assertEquals(element['VALUE'], "tester")
        
    def test_translateOrSingleSubjectRestriction(self):
        restriction = [0x1, [(0x3, (0x00010000, 0x0037001F, (0x0037001F, 'tester')))]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "OR")
        self.assertEquals(element['FIELD'], "subject")
        self.assertEquals(element['COMPARATOR'], "is")
        self.assertEquals(element['VALUE'], "tester")
        
    def test_translateSingleSubjectSubstringRestriction(self):
        restriction = [0x0, [(0x3, (0x00010001, 0x0037001F, (0x0037001F, 'tester and more')))]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "subject")
        self.assertEquals(element['COMPARATOR'], "contains")
        self.assertEquals(element['VALUE'], "tester and more")        
        
    def test_translateSingleSubjectNotEqualsRestriction(self):
        restriction = (0x0, [(0x2, (0x3, (0x00010000, 0x0037001F, (0x0037001F, 'tester667'))))])
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "subject")
        self.assertEquals(element['COMPARATOR'], "is not")
        self.assertEquals(element['VALUE'], "tester667")        
        
    def test_translateSingleContentRestriction(self):
        restriction = [0x0, [(0x3, (0x00010001, mapitags.PR_BODY, (mapitags.PR_BODY, 'tester12323')))]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "body")
        self.assertEquals(element['COMPARATOR'], "contains")
        self.assertEquals(element['VALUE'], "tester12323")
        
    def test_translateDateLTRestriction(self):
        r1 = (0x4, (0x00000000, mapitags.PR_MESSAGE_DELIVERY_TIME, (mapitags.PR_MESSAGE_DELIVERY_TIME, 0)))
        r2 = (0x4, (0x00000002, mapitags.PR_MESSAGE_DELIVERY_TIME, (mapitags.PR_MESSAGE_DELIVERY_TIME, 1287996340)))
        restriction = [0x0, [(0x0, [r1,r2])]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "date")
        self.assertEquals(element['COMPARATOR'], "less than")
        self.assertEquals(element['VALUE'], 1287996340)

    def test_translateDateGTRestriction(self):
        r1 = (0x4, (0x00000002, mapitags.PR_MESSAGE_DELIVERY_TIME, (mapitags.PR_MESSAGE_DELIVERY_TIME, 1287996340)))
        r2 = (0x4, (0x00000000, mapitags.PR_MESSAGE_DELIVERY_TIME, (mapitags.PR_MESSAGE_DELIVERY_TIME, 0)))
        restriction = [0x0, [(0x0, [r1,r2])]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "date")
        self.assertEquals(element['COMPARATOR'], "greater than")
        self.assertEquals(element['VALUE'], 1287996340)
        
    def test_translationSizeLTRestriction(self):
        r1 = (0x4, (0x00000000, mapitags.PR_MESSAGE_SIZE_EXTENDED, (mapitags.PR_MESSAGE_SIZE_EXTENDED, 234567)))
        restriction = [0x0, [r1]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "size")
        self.assertEquals(element['COMPARATOR'], "less than")
        self.assertEquals(element['VALUE'], 234567)

    def test_translationSizeGTRestriction(self):
        r1 = (0x4, (0x00000002, mapitags.PR_MESSAGE_SIZE_EXTENDED, (mapitags.PR_MESSAGE_SIZE_EXTENDED, 234567)))
        restriction = [0x0, [r1]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "size")
        self.assertEquals(element['COMPARATOR'], "greater than")
        self.assertEquals(element['VALUE'], 234567)

    def test_translationSizeEQRestriction(self):
        r1 = (0x4, (0x00000004, mapitags.PR_MESSAGE_SIZE_EXTENDED, (mapitags.PR_MESSAGE_SIZE_EXTENDED, 234567)))
        restriction = [0x0, [r1]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "size")
        self.assertEquals(element['COMPARATOR'], "equals")
        self.assertEquals(element['VALUE'], 234567)

    def test_translateSingleBodyRestriction(self):
        restriction = [0x0, [(0x3, (0x00010000, 0x1000001f, (0x1000001f, 'part of the test')))]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(len(filter), 1)
        element = filter[0]
        self.assertEquals(comp, "AND")
        self.assertEquals(element['FIELD'], "body")
        self.assertEquals(element['COMPARATOR'], "is")
        self.assertEquals(element['VALUE'], 'part of the test')

    def test_translateDoubleBodyRestriction(self):
        r1 = (0x3, (0x00010000, 0x1000001f, (0x1000001f, 'part of the test1')))
        r2 = (0x3, (0x00010000, 0x1000001f, (0x1000001f, 'part of the test2')))
        restriction = [0x1, [r1, r2]]
        comp, filter = MapiRestrictionReader.getFilter(restriction)
        self.assertEquals(comp, "OR")

        self.assertEquals(len(filter), 2)

        element = filter[0]
        self.assertEquals(element['FIELD'], "body")
        self.assertEquals(element['COMPARATOR'], "is")
        self.assertEquals(element['VALUE'], 'part of the test1')

        element = filter[1]
        self.assertEquals(element['FIELD'], "body")
        self.assertEquals(element['COMPARATOR'], "is")
        self.assertEquals(element['VALUE'], 'part of the test2')