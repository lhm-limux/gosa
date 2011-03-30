# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: mapisimplifier.py 1370 2010-11-16 14:03:29Z breucking $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
from libgroupware.base import Groupware, GroupwareTimeout, \
    GroupwareObjectAlreadyExists, \
    GroupwareNoSuchObject, GroupwareError, LOOKUP, READ, STATUS, WRITE, \
    INSERT, POST, \
    CREATE, DELETE, ADMINISTRATE, RIGHTS_NONE, RIGHTS_READ, RIGHTS_POST, \
    RIGHTS_APPEND, RIGHTS_WRITE, RIGHTS_ALL, SMTP, SMTPS, IMAP, IMAPS, \
    POP, POPS, HTTP, ACTIVE, INACTIVE, PENDING, ERROR, \
    OP_MOVE, OP_COPY, OP_FORWARD, OP_MARKAS, OP_DELETE, OP_REPLY, \
    OP_OOOREPLY, GroupwareValueError
import re
from gosa.common.utils import N_
from win32com.mapi import mapi, mapiutil, mapitags

class MapiSimplifier():
    
    session = None
    def __init__(self, workingSession):
        self.session = workingSession
    
    def getFolderString(self, storeEntryId, folderEntryId):
        msgStore = self.session.OpenMsgStore(0,storeEntryId,None,mapi.MDB_NO_DIALOG | mapi.MAPI_BEST_ACCESS)
        msgStoreProps = msgStore.GetProps((mapitags.PR_USER_NAME, mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID, mapitags.PR_DISPLAY_NAME_A),0)
        folderPath = ""
        if type(msgStoreProps[1][1][1]) == type(1) and msgStoreProps[1][1][1] < 1:
            folderPrefix = "user/" + msgStoreProps[1][0][1]
        else:
            folderPrefix = "shared/All Public Folders"
        folder = msgStore.OpenEntry(folderEntryId, None, mapi.MAPI_DEFERRED_ERRORS | mapi.MAPI_BEST_ACCESS)
        if folder is not None:
            name = folder.GetProps((mapitags.PR_URL_NAME_A, mapitags.PR_DISPLAY_NAME_A),0)

        folder = None
        msgStore = None
        return folderPrefix + name[1][0][1]
        
    def createMessage(self, msgText):
        inboxFolder = self.openRecieveFolder()
        message = inboxFolder.CreateMessage(None, mapi.MAPI_DEFERRED_ERRORS | mapi.MAPI_ASSOCIATED)
        message.SetProps([(mapitags.PR_BODY_A, msgText),
                          (mapitags.PR_MESSAGE_CLASS,"IPM.Note.Rules.OofTemplate.Microsoft") # Just for OOReply!!!
                          ])
        KEEP_OPEN_READWRITE = 0x00000002
        FORCE_SAVE = 0x00000004    # save changes and submit
        message.SaveChanges(KEEP_OPEN_READWRITE | FORCE_SAVE)
        entryid = message.GetProps((mapitags.PR_ENTRYID), 0)
        (tag, eid) = entryid[1][0]
        return eid
     
    def findDefaultMsgStore(self):
        messagestorestable = self.session.GetMsgStoresTable(0)
        messagestorestable.SetColumns((mapitags.PR_ENTRYID, mapitags.PR_DISPLAY_NAME_A, mapitags.PR_DEFAULT_STORE),0)

        while True:
            rows = messagestorestable.QueryRows(1, 0)
            #if this is the last row then stop
            if len(rows) != 1:
                break
            row = rows[0]
            #if this is the default store then stop
            if ((mapitags.PR_DEFAULT_STORE,True) in row):
                break

        # unpack the row and open the message store
        (eid_tag, msgeid), (name_tag, name), (def_store_tag, def_store) = row
        return msgeid

    # TODO: rename to correct spelling
    def openRecieveFolder(self):
        eid = self.findDefaultMsgStore();
        msgStore = self.session.OpenMsgStore(0,eid,None,mapi.MDB_NO_DIALOG | mapi.MAPI_BEST_ACCESS)
        eidRecieveFolder = msgStore.GetReceiveFolder(None, 0);
        inboxFolder = msgStore.OpenEntry(eidRecieveFolder[0], None ,mapi.MAPI_BEST_ACCESS)
        return inboxFolder
        
    def getFolder(self, id):
        workingProfile = None
        if workingProfile == None:
            workingProfile = id.split("/")[1]

        try:
            # Get the EMS, PF and PST store IDs
            msgStoresTable = self.session.GetMsgStoresTable(0)

            #self.__get_user_folder(accountId, id, session)
            propTags = [mapitags.PR_PROVIDER_DISPLAY_A,
                mapitags.PR_DISPLAY_NAME_A,
                mapitags.PR_ENTRYID,
                mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID
                ]
            msgStoresRows = mapi.HrQueryAllRows(msgStoresTable, propTags, None, None, 0)

            # Now iterate through each store and print out the top level folder names
            for msgStore in msgStoresRows:
                msgStoreID = msgStore[2][1]
                msgStoreName = msgStore[1][1]
                subtreeEIDTag = None
                #print "Look into ", msgStore
                #TODO: remove hard coded "Postf", "PublicFolders", etc. strings
                #      and use MAPI properties to find out if whether a folder
                #      is public, private or personal
                if (msgStore[0][1] == "Microsoft Exchange Server" or \
                        "Microsoft Exchange Message Store") and \
                        re.search("^Postf", msgStore[1][1]):
                    msgStoreType = "private"
                    path = "user/" + workingProfile
                    subtreeEIDTag = mapitags.PR_IPM_SUBTREE_ENTRYID

                #elif (msgStore[0][1] == "Microsoft Exchange Server" or \
                #        "Microsoft Exchange Message Store") and \
                #        msgStore[1][1] == "Public Folders":
                elif msgStore[3][1] != None:
                    msgStoreType = "public"
                    path = "shared/All Public Folders"
                    subtreeEIDTag = mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID

                elif msgStore[0][1] == "Personal Folders" and re.search("^Temp", msgStore[1][1]):
                    msgStoreType = "personal"
                    subtreeEIDTag = mapitags.PR_IPM_SUBTREE_ENTRYID

                else:
                    continue

                msgStore = self.session.OpenMsgStore(0,
                        msgStoreID,
                        None,
                        mapi.MDB_NO_DIALOG | mapi.MAPI_BEST_ACCESS)

                hr, props = msgStore.GetProps((subtreeEIDTag,), 0)
                subtreeEID = props[0][1]
                subtreeFolder = msgStore.OpenEntry(subtreeEID, None, 0)

                mystore = self.__findSubfolderMsgStore(subtreeFolder,
                        subtreeEIDTag, id, workingProfile, path)

                # If the table was not found go ahead
                if mystore == None:
                    continue

                # Execute the working algorithm
                entryid = mystore.GetProps((mapitags.PR_ENTRYID), 0)
                (tag, eid) = entryid[1][0]
                return msgStoreID, eid

        except (Exception), e:
            raise e
        finally:
            table = None
            acls = None
            foo = None
            mystore = None
            msgStore = None
            subtreeFolderHierarchyRows = None
            subtreeFolderHierarchy = None
            subtreeFolder = None
            # Uninitialise
        return None
        
    def __findSubfolderMsgStore(self, msgStore, subtreeEIDTag, id, workingProfile, path):
        subtreeFolderHierarchy = msgStore.GetHierarchyTable(0)

        # Call the IMAPITable::QueryRows method to list the folders in the top-level folder.
        subtreeFolderHierarchyRows = mapi.HrQueryAllRows(
                subtreeFolderHierarchy,
                [mapitags.PR_DISPLAY_NAME, mapitags.PR_ENTRYID],
                None, None, 0)

        for row in subtreeFolderHierarchyRows:
            if path + "/"  + row[0][1] == id:
                return msgStore.OpenEntry(row[1][1], None, 0)

            elif id.startswith(path  + "/" + row[0][1]):
                store = msgStore.OpenEntry(row[1][1], None, 0)
                sub_store = self.__findSubfolderMsgStore(
                        store,
                        subtreeEIDTag,
                        id, workingProfile,
                        path + "/" + row[0][1])

                if sub_store != None:
                    return sub_store

        # None found
        return None

