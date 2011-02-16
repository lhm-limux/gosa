# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: mapiactionfactory.py 1370 2010-11-16 14:03:29Z breucking $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""

from win32com.mapi import mapitags


class MapiActionFactory():
    @staticmethod
    def createMoveAsMapi(gosaFilter, mapiSimplifier):
        (storeEid, folderEid) = mapiSimplifier.getFolder(gosaFilter["value"])
        storeProperty = (mapitags.PR_ENTRYID,storeEid)
        folderProperty = (mapitags.PR_ENTRYID,folderEid)
        return {'acttype': 1, 'storeEntryId': storeProperty,'folderEntryId': folderProperty}
    @staticmethod
    def createCopyAsMapi(gosaFilter, mapiSimplifier) :
        (storeEid, folderEid) = mapiSimplifier.getFolder(gosaFilter["value"])
        storeProperty = (mapitags.PR_ENTRYID,storeEid)
        folderProperty = (mapitags.PR_ENTRYID,folderEid)
        return {'acttype': 2, 'storeEntryId': storeProperty,'folderEntryId': folderProperty}
    @staticmethod
    def createReplyAsMapi(gosaFilter, mapiSimplifier) :
        return {'acttype': 3, 'message': (mapitags.PR_ENTRYID, mapiSimplifier.createMessage(gosaFilter["value"]))}
    @staticmethod
    def createOofReplyAsMapi(gosaFilter, mapiSimplifier):
        return {'acttype': 4, 'message': (mapitags.PR_ENTRYID, mapiSimplifier.createMessage(gosaFilter["value"]))}
    @staticmethod
    def createDeferActionAsMapi(gosaFilter):
        raise NotImplementedError(N_("Unsupported MAPI filter"))
    @staticmethod
    def createBounceAsMapi(gosaFilter):
        # returns a flag
        return None
    @staticmethod
    def createForwardAsMapi(gosaFilter):
        raise NotImplementedError(N_("Unsupported MAPI filter"))
    @staticmethod
    def createTagAsMapi(gosaFilter):
        raise NotImplementedError(N_("Unsupported MAPI filter"))
    @staticmethod
    def createDeleteAsMapi(gosaFilter):
        return {'acttype': 10}
    @staticmethod
    def createMarkAsReadAsMapi(gosaFilter):
        return {'acttype': 11}
