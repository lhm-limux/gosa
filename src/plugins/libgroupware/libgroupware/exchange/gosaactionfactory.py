# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: gosaactionfactory.py 1370 2010-11-16 14:03:29Z breucking $$

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
from gosa.common.utils import N_
from win32com.mapi import mapitags


class GosaActionFactory():
    """
    GosaAction factory is a utility class to Creates GOsa actions from MAPI
    MAPI Actions. The factory transforms tuple from mapi into GOsa dicts.
    This class provides only static methods, you should not Creates an
    instance.
    """

    @staticmethod
    def createMoveFromMapi(mapiReturn, mapiSimplifier):
        """
        Creates a move action used to move elements into folders. It uses a
        MapiSimplifier instance to retrieve the folder from the MAPI.
        """
        return {'action': OP_MOVE, "value": \
            mapiSimplifier.getFolderString(\
                mapiReturn['actMoveCopy']['storeEntryId'],\
                mapiReturn['actMoveCopy']['fldEntryId']\
            )}

    @staticmethod
    def createCopyFromMapi(mapiReturn, mapiSimplifier):
        """
        Creates a copy action used to copy elements into folders. It uses a
        MapiSimplifier instance to retrieve the folder from the MAPI.
        """
        return  {'action': OP_COPY, "value": \
            mapiSimplifier.getFolderString(\
                mapiReturn['actMoveCopy']['storeEntryId'],\
                mapiReturn['actMoveCopy']['fldEntryId']\
            )}

    @staticmethod
    def createReplyFromMapi(mapiReturn, mapiSimplifier):
        """
        Creates a reply action used to reply mails to sender. It uses a
        MapiSimplifier to retrieve the mail body of the reply message.
        """
        return  {'action': OP_REPLY, "value": \
            mapiSimplifier.getMessageText(\
                mapiReturn['message'][1]\
            )}

    @staticmethod
    def createOofReplyFromMapi(mapiReturn, mapiSimplifier):
        """
        Creates a Out-of-Office reply action used to reply mails to sender.
        It uses a MapiSimplifier to retrieve the mail body of the reply
        message.
        """
        return  {'action': OP_OOOREPLY, "value": \
            mapiSimplifier.getMessageText(\
                mapiReturn['message'][1]\
            )}

    @staticmethod
    def createDeferActionFromMapi():
        """
        (NotImplementedError) Should Creates a defer action.
        """
        raise NotImplementedError(N_("Unsupported MAPI filter"))

    @staticmethod
    def createBounceFromMapi():
        """
        (NotImplementedError) Should Creates a bounce action.
        """
        raise NotImplementedError(N_("Unsupported MAPI filter"))

    @staticmethod
    def createForwardFromMapi(mapiReturn, mapiSimplifier):
        """
        Creates a forward action used to forward mails to a recipient. It uses
        a MapiSimplifier to retrieve the address list from the MAPI.
        """
        return  {'action': OP_FORWARD, "value": \
            mapiSimplifier.getAddressList(\
                mapiReturn['adrlist'][1]\
            )}

    @staticmethod
    def createTagFromMapi():
        """
        (NotImplementedError) Should Creates a tag action.
        """
        raise NotImplementedError(N_("Unsupported MAPI filter"))

    @staticmethod
    def createDeleteFromMapi():
        """
        Create a delete action used to delete mails immediately.
        """
        return {'action': 'delete'}

    @staticmethod
    def createMarkAsReadFromMapi():
        """
        Create a mark as read action used to mark mails as read immediately.
        """
        return {'action': OP_MARKAS, 'value': 'read'}
