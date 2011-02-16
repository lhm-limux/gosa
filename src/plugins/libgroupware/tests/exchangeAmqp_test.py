# -*- coding: utf-8 -*-
from gosa.common.components.jsonrpc_proxy import JSONServiceProxy

import unittest
import win32api
from win32com.mapi import mapi, mapiutil, mapitags
from libgroupware.base import Groupware, GroupwareObjectAlreadyExists, \
    GroupwareNoSuchObject, GroupwareValueError, ACTIVE, INACTIVE, PENDING, \
    RIGHTS_READ, RIGHTS_WRITE, GroupwareTimeout
"""
TODO: GroupwareObjectAlreadyExists check if this exceptions
has got to be tested somewhere here, too
"""

# Create connection to service
proxy = JSONServiceProxy('https://amqp.intranet.gonicus.de:8080/rpc')
proxy.login("admin", "tester")

# List methods
print proxy.getMethods()

# Create samba password hash
print proxy.mksmbhash("secret")


class TestExchangeFunctions(unittest.TestCase):

    proxy = None

    @classmethod
    def setUpClass(cls):
        #Create connection to service 
        proxy = JSONServiceProxy('https://amqp.intranet.gonicus.de:8080/rpc')
        proxy.login("admin", "tester") 
    
    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_helloWorld(self):
        self.assertTrue(proxy)
        cap = proxy.gwGetCapabilities()
        self.assertTrue(len(cap)>0)

    def test_folderList(self):
        flist = proxy.gwFolderList("user/cjer/")
        self.assertTrue(len(flist) > 0)

    def test_folderAdd(self):
        wiwufoldername = "cjer/wiwu/Aufgaben/hallo"
        
        try:
            self.assertTrue(proxy.gwFolderDel(wiwufoldername))
        except:
            pass

        self.assertTrue(proxy.gwFolderAdd(wiwufoldername))
        flist = proxy.gwFolderList("user/cjer/")
        print flist
        self.assertTrue(flist.count(wiwufoldername) == 1)


        self.assertTrue(proxy.gwFolderDel(wiwufoldername))
    """
    def test_folderSetAndGetMembers(self):
        #notExistingFolder = "user/"+self.testuserA+"/Posteingang/Notexisting"
        #folderId = "user/"+self.testuserA+"/Postausgang/Wumperich"
        #newSubFolderId = "user/"+self.testuserA+"/Posteingang/"

        members = proxy.gwFolderGetMembers("user/wiwu/Posteingang")
        self.assertTrue(len(members)>0, "error on permission count")
        print members
        self.assertTrue(len(members)>1)
    """
    def test_getFolderWithMembers(self):
        folders = proxy.gwFolderListWithMembers("user/cjer")
        print folders


    def test_addPublicFolder(self):
        fname ="shared/All Public Folders/testerHape" 
        try:
            proxy.gwFolderDel(fname)
        except:
            pass
        
        result = proxy.gwFolderAdd(fname)
        self.assertTrue(result)
        delRes = proxy.gwFolderDel(fname)
        self.assertTrue(delRes)
