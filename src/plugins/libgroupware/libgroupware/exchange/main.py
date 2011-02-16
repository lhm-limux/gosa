# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: main.py 1392 2010-11-25 13:14:08Z hzerres $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
import os
import platform
import _winreg as winreg
import win32com
import pythoncom
import win32security
import active_directory as ad
import win32com.client
import win32com.adsi
from win32com.mapi import mapi, mapiutil, mapitags
import imaplib
import win32api
import re
import traceback
import copy
import gettext
from datetime import date, datetime, timedelta
from binascii import b2a_hex, a2b_hex
from time import time, sleep, mktime
from datetime import datetime
from ctypes import *
from ctypes.util import find_library
from libgroupware.base import Groupware, GroupwareTimeout, GroupwareObjectAlreadyExists, \
    GroupwareNoSuchObject, GroupwareError, LOOKUP, READ, STATUS, WRITE, INSERT, POST, \
    CREATE, DELETE, ADMINISTRATE, RIGHTS_NONE, RIGHTS_READ, RIGHTS_POST, \
    RIGHTS_APPEND, RIGHTS_WRITE, RIGHTS_ALL, SMTP, SMTPS, IMAP, IMAPS, \
    POP, POPS, HTTP, ACTIVE, INACTIVE, PENDING, ERROR,\
    OP_MOVE, OP_COPY , OP_FORWARD, OP_MARKAS, OP_DELETE, OP_REPLY, \
    OP_OOOREPLY, GroupwareValueError
from gosa.common.components.plugin import Plugin
from gosa.common.components.command import Command
from gosa.common.env import Environment
from gosa.common.utils import N_
from pkg_resources import resource_filename
from libgroupware.exchange.mapirestrictionreader import MapiRestrictionReader
from libgroupware.exchange.mapirestrictionfactory import MapiRestrictionFactory
from libgroupware.exchange.gosaactionfactory import GosaActionFactory
from libgroupware.exchange.mapiactionfactory import MapiActionFactory
from libgroupware.exchange.mapisimplifier import MapiSimplifier

# Include locales
t = gettext.translation('messages', resource_filename("libgroupware.exchange", "locale"),
        fallback=True)
_ = t.ugettext

# Initialize MAPI
#TODO: why is this needed here?
win32com.client.Dispatch("MAPI.Session")
#mapiInitCallback = mapi.MAPIInitialize((mapi.MAPI_INIT_VERSION, mapi.MAPI_MULTITHREAD_NOTIFICATIONS))

class MSExchange(Groupware, Plugin):

    _target_ = 'exchange'

    _mapiToLibGroupwareRightsMap = {
        LOOKUP: mapitags.FRIGHTS_VISIBLE,
        READ: mapitags.FRIGHTS_READ_ANY,
        # STATUS:
        WRITE: mapitags.FRIGHTS_EDIT_ANY,
        # INSERT:
        # POST:
        CREATE: mapitags.FRIGHTS_CREATE,
        DELETE: mapitags.FRIGHTS_DELETE_ANY,
        # ADMINISTRATE:
        RIGHTS_NONE: mapitags.RIGHTS_NONE,
        RIGHTS_READ: mapitags.RIGHTS_READ_ONLY,
        # RIGHTS_POST:
        # RIGHTS_APPEND:
        RIGHTS_WRITE: mapitags.RIGHTS_READ_WRITE,
        RIGHTS_ALL: mapitags.RIGHTS_ALL
        #TODO: Missing mapitags.FRIGHTS_CREATE_SUBFOLDER
        #TODO: Missing mapitags.FRIGHTS_OWNER
        #TODO: Missing mapitags.FRIGHTS_CONTACT
        }

    ACTIONS_KEY = "actions"
    ACTION_KEY = "action"

    _supportedProperties = {
            SMTP: {
                'default': True,
                'read-only': True,
            },
            SMTPS: {
                'default': False,
                'read-only': True,
            },
            POP: {
                'default': True,
                'read-only': False,
            },
            IMAP: {
                'default': True,
                'read-only': False,
            },
            POPS: {
                'default': False,
                'read-only': True
            },
            IMAPS: {
                'default': False,
                'read-only': True,
            },
            HTTP: {
                'default': True,
                'read-only': False,
            },
        }

    def __init__(self):
        """
        Initialization of the MSExchange management class.
        """
        self.env = Environment.getInstance()
        self.env.log.info("initializing exchange groupware plugin")

        # Bail out if the permissions are bad
        if not self.__is_domain_admin():
            raise Exception(N_("Service needs to be run in a domain administrator context"))

        # Mapi Initialisation
        mapi.MAPIInitialize((mapi.MAPI_INIT_VERSION, mapi.MAPI_MULTITHREAD_NOTIFICATIONS))

        # Load exchange path
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Exchange\Setup")
        dll_path = winreg.QueryValueEx(key, 'Services')[0] + r"\bin"
        key.Close()

        # Set os.path for Exchange cdoexm DLL
        self.env.log.debug("adding '%s' to DLL path" % dll_path)
        os.environ["PATH"] += ";" + dll_path

        # Base DN and domain
        self.domain = ad.root().dc
        self.__baseDN = ad.root().distinguishedName
        self.env.log.debug("found base DN '%s'" % self.__baseDN)

        # Works, if the path is set to include the cdoexm.dll
        self.__cdoexm = cdll.LoadLibrary(find_library("cdoexm"))

        # Locate MDB's
        cfg = ad.AD_object("LDAP://CN=configuration," + self.__baseDN)
        self.__publicMDB = {}
        for folder in cfg.search("objectClass='msExchPublicMDB'"):
            self.env.log.debug("adding public MDB '%s'" % folder.cn)
            self.__publicMDB[folder.cn] = "LDAP://" + folder.distinguishedName
        self.__privateMDB = {}
        for folder in cfg.search("objectClass='msExchPrivateMDB'"):
            self.env.log.debug("adding private MDB '%s'" % folder.cn)
            self.__privateMDB[folder.cn] = "LDAP://" + folder.distinguishedName

    def __del__(self):
        mapi.MAPIUninitialize()

    @Command()
    def getLocalDomains(self):
        """ Return local domains """
        return [self.domain]

    @Command()
    def getFilterFeatures(self):
        """
        Return list of possible filter features.
        
        @rtype: list
        @return: list of possible filter features
        """
        return [
            {'filter': 'subject', 'COMPARATOR': 'STRING'},
            # Filter From Not possible because PyWin32 does not support needed 
            # restriction type
            #{'filter': 'from', 'COMPARATOR': 'STRING'},
            {'filter': 'body', 'COMPARATOR': 'STRING'},
            {'filter': 'date', 'COMPARATOR': 'INT'},
            {'filter': 'priority', 'COMPARATOR': 'INT'},
            # Filter To Not possible because PyWin32 does not support needed 
            # restriction type
            #{'filter': 'to', 'COMPARATOR': 'STRING'}, 
            {'filter': 'size', 'COMPARATOR': 'INT'}
            ]
    
    @Command()
    def getCapabilities(self):
        """ Get capabilities of groupware handler """
        return super(MSExchange, self).getCapabilities()

    @Command()
    def getMailboxLocations(self):
        """ List available mailbox locations """
        super(MSExchange, self).getMailboxLocations()

        tmp = self.__privateMDB.copy()
        tmp.update(self.__publicMDB)
        return tmp.keys()

    @Command()
    def acctList(self, rdn="cn=Users"):
        """ List exchange enabled users """
        super(MSExchange, self).acctList(rdn)

        base = ad.AD_object("LDAP://" + ",".join([rdn, self.__baseDN]))
        return dict((v.sAMAccountName, v.mail)
            for v in base.search("objectClass='user'", "mail='*'"))

    @Command()
    def acctAdd(self, id, address, location=None, rdn="cn=Users"):
        """ Add mail account """
        super(MSExchange, self).acctAdd(id, address)

        # Bail out if the account already exists
        #TODO: not true for 100%. we eventually need to UPDATE an existing
        #      account to be exchange enabled.
        if self.acctExists(id):
            raise GroupwareObjectAlreadyExists(N_("Account object '%s' already exists"), id)

        # Bail out if address is in use
        if self.mailAddressExists(address):
            raise GroupwareValueError(N_("'%s' is already in use"), address)

        # Fill location if not available
        if not location:
            if len(self.__privateMDB) != 1:
                raise GroupwareValueError(N_("No default location for mailbox available"))
            else:
                location = self.__privateMDB.keys()[0]

        # Bail out if location is no valid private MDB
        if not location in self.__privateMDB.keys():
            raise GroupwareValueError(N_("Location '%s' does not exist"), location)

        # Get AD container object
        ad_obj = win32com.client.GetObject("LDAP://%s,%s" % (rdn, self.__baseDN))

        # Create user stub in ad
        ad_user = ad_obj.Create('user', 'cn=%s' % id)
        ad_user.Put('sAMAccountName', id)
        ad_user.Put('userPrincipalName', "%s" % address)
        ad_user.Put('DisplayName', id)
        ad_user.Put('givenName', id)
        ad_user.Put('sn', id)

        # Commit data
        ad_user.SetInfo()
        ad_user.GetInfo()

        # Set dummy credentials, password will be set elsewhere
        import string
        from random import Random
        ad_user.AccountDisabled = 0
        randomUserPassword = ''.join(Random().sample(string.letters + string.digits, 12))
        ad_user.setpassword(randomUserPassword)
        ad_user.Put('pwdLastSet', -1)
        ad_user.SetInfo()

        # Create mailbox
        ad_user.CreateMailbox(self.__privateMDB[location])
        ad_user.SetInfo()

        # Set mail address and set to ADS_UF_NORMAL_ACCOUNT
        ad_user.EmailAddress = address
        ad_user.SetInfo()
        ad_user.Put('mail', address)
        ad_user.Put('mailNickname', id)
        ad_user.Put('msExchUserAccountControl', 2)
        ad_user.EnableStoreDefaults = True
        ad_user.SetInfo()

        # Check if account is present
        for i in range(0, 60):
            if self.acctGetStatus(id)['status'] != PENDING:
                break
            sleep(1)
        else:
            raise GroupwareTimeout(N_("Timeout while adding account '%s'"), id)

        self._imapConnection(id, randomUserPassword)

        return True

    @Command()
    def acctSetEnabled(self, id, enable):
        """ Enable or disable mail account """
        super(MSExchange, self).acctSetEnabled(id, enable)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        val = ad_obj.get('userAccountControl')

        if enable:
            val = val & ~2
        else:
            val = val | 2

        ad_obj.Put('userAccountControl', val)
        ad_obj.Put('msExchUserAccountControl', 2 if enable else 0)
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctDel(self, id, purge = False):
        """ Remove mail account """
        super(MSExchange, self).acctDel(id)

        # Remove user
        #TODO: not true for 100%. we eventually need to UPDATE an existing
        #      account to be exchange disabled.
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        if purge:
            ad_obj.DeleteMailbox()
        ad_obj.parent().delete("user", "cn=%s" % ad_obj.cn)

        return True

    @Command()
    def acctExists(self, id):
        """ Check if mail account exists """
        super(MSExchange, self).acctExists(id)
        return ad.find_user(id) != None

    @Command()
    def acctGetLocation(self, id):
        """ Get mail storage location """
        super(MSExchange, self).acctGetLocation(id)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        for mdb, path in self.__privateMDB.iteritems():
            if path == ad_obj.homeMDB:
                return mdb

        return None

    @Command()
    def acctSetLocation(self, id, location):
        """ Set mail storage location """
        super(MSExchange, self).acctSetLocation(id)

        # Bail out if location is no valid private MDB
        if not location in self.__privateMDB.keys():
            raise GroupwareValueError(N_("Location '%s' does not exist"), location)

        # Load user
        ad_user = ad.find_user(id)
        ad_user.GetInfo()

        # Any changes?
        if ad_user.homeMDB == self.__privateMDB[location]:
            return True

        # Move box
        ad_user.MoveMailbox(self.__privateMDB[location])
        return ad_user.SetInfo()

    @Command()
    def acctAddAlternateMailAddress(self, id, address):
        """ Add alternative mail address """
        super(MSExchange, self).acctAddAlternateMailAddress(id, address)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = list(ad_obj.Get("proxyAddresses"))

        # Check if it's not listed in alternate/primary address
        if not address.lower() in [addr[5:].lower()
            for addr in raw
            if addr.lower().startswith("smtp:")]:

            raw.insert(0, u"smtp:" + address)
        else:
            raise GroupwareValueError(N_("'%s' is already in the list of alternate mail addresses"), address)

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctDelAlternateMailAddress(self, id, address):
        """ Delete alternative mail address """
        super(MSExchange, self).acctDelAlternateMailAddress(id, address)

        # Get AD User ID object234
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = list(ad_obj.Get("proxyAddresses"))

        if address.lower() in [addr[5:].lower()
            for addr in raw
            if addr.startswith("smtp:")]:

            raw.remove(u"smtp:" + address)
        else:
            return False

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetAlternateMailAddresses(self, id):
        """ Get list of alternative mail addresses """
        super(MSExchange, self).acctGetAlternateMailAddresses(id)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = list(ad_obj.Get("proxyAddresses"))

        return [addr[5:] for addr in raw if addr.startswith("smtp:")]

    @Command()
    def acctSetAlternateMailAddresses(self, id, addresses):
        """ Set list of alternative mail addresses """
        super(MSExchange, self).acctSetAlternateMailAddresses(id, addresses)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = list(ad_obj.Get("proxyAddresses"))

        # Remove all existing smtp: addresses from the proxy addresses
        for address in [addr for addr in raw if addr.startswith("smtp:")]:
            raw.remove(address)

        if len(addresses) > 0:
            # Add all supplied addresses to the proxies
            for address in list(set(addresses)):
                raw.insert(0, u"smtp:" + address)

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctAddMailForwardAddress(self, id, address, redirect):
        """ Add forward address """
        super(MSExchange, self).acctAddMailForwardAddress(id, address, redirect)

        # Check if MailForward is set
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        recipient = None
        try:
            recipient = ad_obj.Get('altRecipient')
        except:
            pass

        # Bail out if there's already one recipient in the list
        if recipient:
            raise GroupwareValueError(N_("Only one forward mail address allowed"))

        # Search for ad DN with that mail address
        recipient = None
        for person in ad.search("mail='%s'" % address):
            recipient = person.distinguishedName
            break
        else:
            raise GroupwareValueError(N_("'%s' is not assigned in active directory"), address)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        ad_obj.Put('altRecipient', recipient)
        ad_obj.Put('deliverAndRedirect', not redirect)
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctDelMailForwardAddress(self, id, address):
        """ Remove forward address """
        super(MSExchange, self).acctDelMailForwardAddress(id, address)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Bail out if address is not in use
        try:
            target_dn = ad_obj.Get("altRecipient")
        except:
            raise GroupwareValueError(N_("'%s' not in forwarders"), address)

        # Load target object and check mail address
        target_obj = ad.AD_object("LDAP://" + target_dn)
        if target_obj.Get("mail") != address:
            raise GroupwareValueError(N_("'%s' not in forwarders"), address)

        # Remove attributes
        ad_obj.PutEx(1, 'altRecipient', 0)
        ad_obj.PutEx(1, 'deliverAndRedirect', 0)
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetMailForwardAddresses(self, id):
        """ Get list of forward addresses """
        super(MSExchange, self).acctGetMailForwardAddresses(id)

        # Get AD User ID object1
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Bail out if address is not in use
        try:
            target_dn = ad_obj.Get("altRecipient")
        except:
            return []

        target_obj = ad.AD_object("LDAP://" + target_dn)
        redirect = False
        try:
            redirect = bool(target_obj.Get("deliverAndRedirect"))
        except:
            pass

        return {target_obj.Get("mail"): redirect}

    @Command()
    def acctSetMailForwardAddresses(self, id, addresses):
        """ Set list of forward addresses """
        super(MSExchange, self).acctSetMailForwardAddresses(id, addresses)

        # Setting mail forwarder works only for one address
        if len(addresses) > 1:
            raise GroupwareValueError(N_("Only one forward mail address allowed"))

        # delete entry if exists
        if len(addresses) == 0:
            # Get AD User ID object
            ad_obj = ad.find_user(id)
            ad_obj.GetInfo()

            # Bail out if address is not in use
            try:
                target_dn = ad_obj.Get("altRecipient")
            except:
                # no entry found => return
                return True

            # Remove attributes
            ad_obj.PutEx(1, 'altRecipient', 0)
            ad_obj.PutEx(1, 'deliverAndRedirect', 0)
            ad_obj.SetInfo()
            ad._CACHE = {}

            return True

        # Load first element
        try:
            for address, redirect in addresses.iteritems():
                break
        except:
            raise GroupwareValueError(N_("Please add forwarders using key value pairs"))

        # Search for ad DN with that mail address
        recipient = None
        for person in ad.search("mail='%s'" % address):
            recipient = person.distinguishedName
            break
        else:
            raise GroupwareValueError(N_("'%s' is not assigned in active directory"), address)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        ad_obj.Put('altRecipient', recipient)
        ad_obj.Put('deliverAndRedirect', not redirect)
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetQuota(self, id):
        """ Retrieve quota settings """
        super(MSExchange, self).acctGetQuota(id)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Get quota usage
        server = ad_obj.Get("msExchHomeServerName").split("=")[-1].lower()

        result = {
            "hold": ad_obj.DaysBeforeGarbageCollection,
            "usage": self.__get_user_quota(server, id),
            }
        for key, value in {"warn_limit": "mDBStorageQuota",
            "send_limit": "mDBOverQuotaLimit",
            "hard_limit": "mDBOverHardQuotaLimit"}.items():
            try:
                result[key] = ad_obj.Get(value)
            except:
                result[key] = None

        return result

    @Command()
    def acctSetQuota(self, id, warn_limit, send_limit, hard_limit, hold = None):
        """ Set quota settings """
        super(MSExchange, self).acctSetQuota(id, warn_limit, send_limit, hard_limit, hold)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Enabled defaults if everything is set to None
        enabled = not warn_limit and not send_limit and not hard_limit and not hold
        ad_obj.EnableStoreDefaults = enabled

        try:
            # Transfer values      
            ad_obj.StoreQuota = int(warn_limit) if warn_limit else 0
            ad_obj.Put("mDBStorageQuota", ad_obj.StoreQuota)
        except Exception, e:
            raise GroupwareValueError(N_("Setting warn_limit failed: %s"), str(e))
        
        try: 
            ad_obj.OverQuotaLimit = int(send_limit) if send_limit else 0
            ad_obj.Put("mDBOverQuotaLimit", ad_obj.OverQuotaLimit) 
        except Exception, e:
            raise GroupwareValueError(N_("Setting send_limit failed: %s"), str(e))

        try:
            ad_obj.HardLimit = int(hard_limit) if hard_limit else 0
            ad_obj.Put("mDBOverHardQuotaLimit", ad_obj.HardLimit)

        except Exception, e:
            raise GroupwareValueError(N_("Setting hard_limit failed: %s"), str(e))
        
        if hold:
            try:
                ad_obj.hold = int(hold) if hold else 0
                ad_obj.Put("hold", ad_obj.hold)
            except Exception, e:
                # TODO:
                # implement the hold parameter or change the interface
                #raise GroupwareValueError(N_("Setting hold failed: %s"), str(e))
                pass

        # Commit data
        ad_obj.SetInfo()
        ad._CACHE = {}
        return True

    @Command()
    def acctGetMailLimit(self, id):
        """ Retrieve mail limit settings """
        super(MSExchange, self).acctGetMailLimit(id)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        try:
            res_send = ad_obj.Get("submissionContLength")
        except:
            res_send = None

        try:
            res_recv = ad_obj.Get("delivContLength")
        except:
            res_recv = None

        return {
            "send": res_send,
            "receive": res_recv,
        }

    @Command()
    def acctSetMailLimit(self, id, send, receive):
        """ Set mail limit settings """
        super(MSExchange, self).acctSetMailLimit(id, send, receive)

        # Get AD User ID object
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Check send / receive values
        if send and send < 0:
            raise GroupwareValueError(N_("Send value needs to be zero or above"))
        if receive and receive < 0:
            raise GroupwareValueError(N_("Receive value needs to be zero or above"))

        # Push values
        ad_obj.Put("submissionContLength", int(send) if send else 0)
        ad_obj.Put("delivContLength", int(receive) if receive else 0)

        # Commit data
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetStatus(self, id):
        """ Check account status """
        super(MSExchange, self).acctGetStatus(id)

        ad._CACHE = {}
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        try:
            addr = ad_obj.Get('proxyAddresses')
        except:
            return {'status': PENDING, 'message': None}

        if ad_obj.Get('userAccountControl') & 2:
            return {'status': INACTIVE, 'message': None}

        #TODO: library calls should set error messages and
        #      internal state later on
        return {'status': ACTIVE, 'message': None}

    @Command()
    def distGetStatus(self, id):
        """ Check distribution list status """
        super(MSExchange, self).distGetStatus(id)

        ad._CACHE = {}
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        try:
            addr = ad_obj.Get('proxyAddresses')
        except:
            return {'status': PENDING, 'message': None}

        #TODO: library calls should set error messages and
        #      internal state later on
        return {'status': ACTIVE, 'message': None}

    @Command()
    def acctGetProperties(self, id):
        """ Get mail account properties """
        super(MSExchange, self).acctGetProperties(id)

        # Get account protocol settings
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        try:
            settings = ad_obj.get('protocolSettings')
        except:
            return HTTP | SMTP | SMTPS | IMAP | IMAPS | POP | POPS

        # Multivalue
        result = SMTP | SMTPS
        for setting in [s.encode('utf-8') for s in settings]:
            if setting.startswith("IMAP4§1"):
                result |= IMAP | IMAPS
                continue
            if setting.startswith("POP3§1"):
                result |= POP | POPS
                continue
            if setting.startswith("HTTP§1"):
                result |= HTTP
                continue

        return result

    @Command()
    def acctSetProperties(self, id, props):
        """ Set mail account properties """
        super(MSExchange, self).acctSetProperties(id, props)

        # Get account protocol settings
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Fetch existing properties
        http = u"§1§§§§§§"
        imap4 = u"§1§4§DIN_66003§0§1§0§0"
        pop3 = u"§1§4§DIN_66003§0§1§0§0"

        try:
            settings = ad_obj.get('protocolSettings')
            for setting in settings:
                if setting.startswith(u"IMAP4§"):
                    imap4 = setting[7:]
                    continue
                if setting.startswith(u"POP3§"):
                    pop3 = setting[6:]
                    continue
                if setting.startswith(u"HTTP§"):
                    http = setting[6:]
                    continue
        except:
            pass

        # Build final value
        settings = (
            u"HTTP§%d%s" % (int(bool(props & HTTP)), http),
            u"POP3§%d%s" % (int(bool(props & POP | props & POPS)), pop3),
            u"IMAP4§%d%s" % (int(bool(props & IMAP | props & IMAPS)), imap4),
            )
        ad_obj.Put('protocolSettings', settings)

        # Commit data
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetPrimaryMailAddress(self, id):
        """ Get mail account primary address """
        super(MSExchange, self).acctGetPrimaryMailAddress(id)
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        return ad_obj.Get('mail')

    @Command()
    def acctSetPrimaryMailAddress(self, id, address):
        """ Set mail account primary address """
        super(MSExchange, self).acctSetPrimaryMailAddress(id, address)

        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()

        # Sanity check if there's a proxy address to check
        if not ad_obj.proxyAddresses:
            raise GroupwareValueError(N_("Object '%s' has no proxy addresses"), id)

        # Just skip if there's no change
        if address in [a[5:] for a in ad_obj.proxyAddresses if a.startswith("SMTP:")]:
            return True

        # Bail out if address is in use
        if self.mailAddressExists(address):
            raise GroupwareValueError(N_("'%s' is already in use"), address)

        # Set information
        ad_obj.Put('mail', address)
        proxy = []
        for addr in ad_obj.proxyAddresses:
            if addr.startswith("SMTP:"):
                proxy.append(u"SMTP:" + address)
            else:
                proxy.append(addr)

        ad_obj.Put("proxyAddresses", proxy)
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def acctGetOutOfOfficeReply(self, id):
        """ Get out of office settings """
        super(MSExchange, self).acctGetOutOfOfficeReply(id)

        # Load server name
        ad_obj = ad.find_user(id)
        ad_obj.GetInfo()
        server = ad_obj.Get("msExchHomeServerName").split("=")[-1].lower()

        # Store current workdirectory due to a problem with
        # the session API and retrieve the session.
        cwd = os.getcwd()
        session = win32com.client.Dispatch("MAPI.Session")

        # Log in and return information
        session.Logon('', '', False, True, True, True, server + '\n' + id)

        # Don't return anything if there's no out of office
        if not session.OutOfOffice:
            return False

        #TODO: add begin/end
        result = {
            'message': session.OutOfOfficeText,
            'begin': None,
            'end': None,
            }

        # Log off and restore directory
        session.Logoff()
        os.chdir(cwd)

        return result

    @Command()
    def acctSetOutOfOfficeReply(self, id, msg = None, begin = None, end = None):
        """Set out of Office reply via Ceo """
        super(MSExchange, self).acctSetOutOfOfficeReply(id, msg, begin, end)
        # Load server name
        ad_obj = ad.find_user(id)
        server = ad_obj.Get("msExchHomeServerName").split("=")[-1].lower()
        
        # Store current workdirectory due to a problem with
        # the session API and retrieve the session.
        cwd = os.getcwd()
        session = win32com.client.Dispatch("MAPI.Session")
        
        # Log in and return information
        session.Logon('', '', False, True, True, True, server + '\n' + id)
        
        #TODO: add begin/end - ignore the time at the moment.

        #if begin != None and end != None:
        #    raise GroupwareValueError("begin/end not supported yet - please use None")
        
        if msg:
            session.OutOfOfficeText = msg
            session.OutOfOffice = True
        else:
            session.OutOfOffice = False
        
        # Log off and restore directory
        session.Logoff()
        os.chdir(cwd)
        return True

    @Command()
    def distList(self, rdn = "CN=Users"):
        """ List distribution lists """
        super(MSExchange, self).distList(rdn)
        ad._CACHE = {}
        base = ad.AD_object("LDAP://" + ",".join([rdn, self.__baseDN]))
        dList =  dict((v.cn, v.mail)
            for v in base.search("objectClass='group'", "groupType='2'", "mail='*'"))
        return dList

    @Command()
    def distAdd(self, id, address, location = None, rdn = "CN=Users"):
        """ Add distribution list """
        super(MSExchange, self).distAdd(id, address, location, rdn)

        # Bail out if address is in use
        if self.mailAddressExists(address):
            raise GroupwareValueError(N_("'%s' is already in use"), address)

        # Fill location if not available
        if not location:
            if len(self.__publicMDB) != 1:
                raise GroupwareValueError(N_("No default location for mailbox available"))
            if len(self.__publicMDB) == 1:
                location = self.__publicMDB.keys()[0]

        # Bail out if location is no valid private MDB
        if not location in self.__publicMDB.keys():
            raise GroupwareValueError(N_("Location '%s' does not exist"), location)

        # Get AD container object
        ad_obj = win32com.client.GetObject("LDAP://%s,%s" % (rdn, self.__baseDN))

        # Create Folder stub in ad
        ad_group = ad_obj.Create('group', 'cn=%s' % id)
        ad_group.Put('mail', address)
        ad_group.Put('mailNickname', id)
        ad_group.Put('msExchALObjectVersion', 21)
        ad_group.Put('reportToOriginator', True)
        ad_group.Put('groupType', 2)
        ad_group.MailEnable()
        ad_group.Put('proxyAddresses', [u'SMTP:%s' % address])

        # Commit data
        ad_group.SetInfo()
        ad._CACHE = {}

        # Check if list is present
        for i in range(0, 60):
            if self.distGetStatus(id)['status'] != PENDING:
                break
            sleep(1)
        else:
            raise GroupwareTimeout(N_("Timeout while adding distribution list '%s'"), id)

        return True

    @Command()
    def distRename(self, id, new_id, rdn="cn=Users"):
        """ Rename distribution list """
        super(MSExchange, self).distDel(id)

        ad_obj = ad.find_group(id)
        source = win32com.client.GetObject("LDAP://" + ad_obj.distinguishedName)
        target = win32com.client.GetObject("LDAP://" + rdn + "," + self.__baseDN)
        target.MoveHere(source.ADsPath, "CN=" + new_id)

        return True

    @Command()
    def distDel(self, id):
        """ Remove distribution list """
        super(MSExchange, self).distDel(id)

        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()
        ad_obj.parent().delete("group", "cn=%s" % ad_obj.cn)

        return True

    @Command()
    def distExists(self, id):
        """ Check if distribution list exists """
        super(MSExchange, self).distExists(id)

        return ad.find_group(id) != None

    @Command()
    def distGetMembers(self, id):
        """ Get members of distribution list """
        super(MSExchange, self).distGetMembers(id)

        # Load group
        ad_group = ad.find_group(id)
        ad_group.GetInfo()
        # Build result set
        members = ad_group.member
        result = []
        for member in ad_group.member:
            result.append(member.Get('mail'))

        return result

    @Command()
    def distAddMember(self, id, address):
        """ Add member to distribution list """
        super(MSExchange, self).distAddMember(id, address)

        # We can only add addresses of local users here, so check if there's
        # one with the matching mail address.
        for user in ad.search("proxyAddresses='smtp:%s'" % address,
            "proxyAddresses='SMTP:%s'" % address):
            ad_user = user
            break
        else:
            raise GroupwareValueError(N_("No local user with address '%s' available") % address)

        # Load ad group
        ad_group = ad.find_group(id)
        ad_group.GetInfo()

        # Get member list
        try:
            members = ad_group.Get('member')
        except:
            members = []

        # List conversion
        if isinstance(members, basestring):
            members = [members]

        # Member already there?
        if ad_user.distinguishedName in members:
            raise GroupwareValueError(N_("'%s' is already member of '%s'"), address, id)

        # Commit data
        members.append(ad_user.distinguishedName)
        ad_group.Put('member', members)
        ad_group.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def distDelMember(self, id, address):
        """ Remove member from distribution list """
        super(MSExchange, self).distDelMember(id, address)

        # Find user DN with the given address
        for user in ad.search("proxyAddresses='smtp:%s'" % address,
            "proxyAddresses='SMTP:%s'" % address):

            ad_user = user
            break
        else:
            raise GroupwareValueError(N_("No local user with address '%s' available") % address)

        # Get AD dist ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        try:
            members = ad_obj.Get('member')
            if not ad_user.distinguishedName in members:
                raise Exception()
        except:
            raise GroupwareNoSuchObject(N_("'%s' has no member with address '%s'"), id, address)

        # Commit changes
        ad_obj.PutEx(4, 'member', [ad_user.distinguishedName])
        ad_obj.SetInfo()
        ad._CACHE = {}

        return True

    @Command()
    def distGetPrimaryMailAddress(self, id):
        """ Get distribution list primary mail address """
        super(MSExchange, self).distGetPrimaryMailAddress(id)

        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        addr = ad_obj.proxyAddresses
        if isinstance(addr, basestring):
            addr = [addr]
        return [a[5:] for a in addr if a.startswith("SMTP:")][0]

    @Command()
    def distSetPrimaryMailAddress(self, id, address):
        """ Set distribution list primary mail address """
        super(MSExchange, self).distSetPrimaryMailAddress(id, address)

        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Sanity check if there's a proxy address to check
        if not ad_obj.proxyAddresses:
            raise GroupwareNoSuchObject(N_("Object '%s' has no proxy addresses"), id)

        # Just skip if there's no change
        if address in [a[5:] for a in ad_obj.proxyAddresses if a.startswith("SMTP:")]:
            return True

        # Bail out if address is in use
        if self.mailAddressExists(address):
            raise GroupwareValueError(N_("'%s' is already in use"), address)

        # Set information
        #ad_obj.Put('mail', address)
        # Get proxyAddresses list
        raw = ad_obj.Get("proxyAddresses")
        if isinstance(raw, basestring):
            raw = [raw]
            raw = list(raw)
        proxy = []
        for addr in raw:
            if addr.startswith("SMTP:"):
                proxy.append(u"SMTP:" + address)
            else:
                proxy.append(addr)

        ad_obj.Put("proxyAddresses", proxy)
        ad_obj.SetInfo()

        return True

    @Command()
    def distGetAlternateMailAddresses(self, id):
        """ Get list of distribution list alternate mail addresses """
        super(MSExchange, self).distGetAlternateMailAddresses(id)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = list(ad_obj.Get("proxyAddresses"))
        return [addr[5:] for addr in raw if addr.startswith("smtp:")]

    @Command()
    def distSetAlternateMailAddresses(self, id, addresses):
        """ Set list of distribution list alternate mail addresses """
        super(MSExchange, self).distSetAlternateMailAddresses(id, addresses)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = ad_obj.Get("proxyAddresses")
        if isinstance(raw, basestring):
            raw = [raw]
        else:
            raw = list(raw)

        # Remove all existing smtp: addresses from the proxy addresses
        for address in [addr for addr in raw if addr.startswith("smtp:")]:
            raw.remove(address)

        # Add all supplied addresses to the proxies
        for address in list(set(addresses)):
            raw.insert(0, u"smtp:" + address)

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()

        return True

    @Command()
    def distAddAlternateMailAddress(self, id, address):
        """ Add alternate mail address to distribution list """
        super(MSExchange, self).distAddAlternateMailAddress(id, address)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = ad_obj.Get("proxyAddresses")
        if isinstance(raw, basestring):
            raw = [raw]
        raw = list(raw)

        # Check if it's not listed in alternate/primary address
        if not address.lower() in [addr[5:].lower()
            for addr in raw
            if addr.lower().startswith("smtp:")]:

            raw.insert(0, u"smtp:" + address)
        else:
            raise GroupwareValueError(N_("'%s' is already in the list of alternate mail addresses"), address)

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()

        return True

    @Command()
    def distDelAlternateMailAddress(self, id, address):
        """ Remove alternate mail address from distribution list """
        super(MSExchange, self).distDelAlternateMailAddress(id, address)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Get proxyAddresses list
        raw = ad_obj.Get("proxyAddresses")
        if isinstance(raw, basestring):
            raw = [raw]
        raw = list(raw)

        if address.lower() in [addr[5:].lower()
            for addr in raw
            if addr.startswith("smtp:")]:

            raw.remove(u"smtp:" + address)
        else:
            raise GroupwareNoSuchObject(N_("Address '%s' does not exist"), address)

        # Commit data
        ad_obj.Put("proxyAddresses", tuple(raw))
        ad_obj.SetInfo()

        return True

    @Command()
    def distGetMailLimit(self, id):
        """ Get distribution list mail limits """
        super(MSExchange, self).distGetMailLimit(id)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        try:
            res_recv = ad_obj.Get("delivContLength")
        except:
            res_recv = None

        return {
            "receive": res_recv,
        }

    @Command()
    def distSetMailLimit(self, id, receive = None):
        """ Set distribution list mail limits """
        super(MSExchange, self).distSetMailLimit(id, receive)

        # Get AD User ID object
        ad_obj = ad.find_group(id)
        ad_obj.GetInfo()

        # Check send / receive values
        if receive and receive < 0:
            raise GroupwareValueError(N_("Receive value needs to be zero or above"))

        # Push value
        ad_obj.Put("delivContLength", int(receive) if receive else 0)

        # Commit data
        ad_obj.SetInfo()

        return True

    @Command()
    def folderList(self, id = None):
        """ Retrieve folder list
        global folders when the id is not set
        get the Folderlist of id otherwise
        """
        super(MSExchange, self).folderList(id)

        folders = []

        # Get all folders?
        if not id:
            # Shared folders
            folders.extend(self.__get_global_folders())

            # set the id to shares, to deliver only public folders.
            id = "shared"
            # All users
            for user in self.acctList():
                try:
                    folders.extend(self.__get_user_folders(str(user)))
                except:
                    pass
        else:
            # Load shared folder list?
            if id.startswith("shared"):
                folders.extend(self.__get_global_folders())

            # Load complete user list?
            if id == "user" or id == "user/":
                for user in self.acctList():
                    try:
                        folders.extend(self.__get_user_folders(str(user)))
                    except:
                        pass

            elif id.startswith("user/"):
                try:
                    folders.extend(self.__get_user_folders(id.split("/")[1]))
                except Exception as e:
                    self.env.log.debug(e)
                    self.env.log.debug(traceback.format_exc())
                    raise GroupwareNoSuchObject(N_("Folder '%s' does not exist"), id)

        if len(folders) > 0:
            return filter(lambda s: s.startswith(id), folders)
        else:
            return folders

    @Command()
    def folderExists(self, id):
        """ Check if folder exists """
        super(MSExchange, self).folderExists(id)

        #TODO: this can be optimized
        for id in self.folderList(id):
            return True
        return False

    @Command()
    def folderAdd(self, id):
        """ Add new folder """
        super(MSExchange, self).folderAdd(id)

        # Find base and folder name
        base = "/".join(id.split("/")[:-1])
        name = id.split("/")[-1]

        # Get folder object

        folder = self.__get_folder(base)

        """ Add new folder """
        try:
            folder.RootFolder.Folders.Add(name)
        except Exception as e:
            try:
                folder.Folders.Add(name)
            except:
                self.env.log.error("cannot add folder %s" % (base + name))
                return False

        return True

    @Command()
    def folderDel(self, id):
        """ Delete existing folder """
        super(MSExchange, self).folderDel(id)

        # Get folder object and remove it
        folder = self.__get_folder(id)
        folder.Delete()

        return True

    @Command()
    def folderGetMembers(self, id, session = None):
        """ Get members for folder """
        super(MSExchange, self).folderGetMembers(id)

        self.env.log.debug("Call folderGetMembers")

        #if not self.folderExists(id):
        #    raise GroupwareNoSuchObject

        def transformAclTableToDict(store):
            self.env.log.debug("Transform ACL Table to dict (%s)" % id)

            prop = store.OpenProperty(
                mapitags.PR_ACL_TABLE,
                mapi.IID_IExchangeModifyTable,
                0,
                mapi.MAPI_DEFERRED_ERRORS)

            members = dict()
            table = prop.GetTable(0)
            count = table.GetRowCount(0)
            acls = mapi.HrQueryAllRows(table, None, None, None, count)

            for acl in acls:
                member = self.__getGosaUserFromEntryId(acl[2][1])
                if member == None:
                    pass
                else:
                    members[member] = self.__getLibgroupwareRightsFlag( \
                        acl[4][1])
 
            return members

        if id.startswith("shared"):
            accountId = self.env.config.getOption("admin_id", "exchange")
            return self.__workOnFolder(id, transformAclTableToDict, accountId, \
                session)
        else:
            self.env.log.debug("User folder")
            accountId = id.split("/")[1]
            return self.__workOnFolder(id, transformAclTableToDict, accountId, \
                session)


    def __getGosaUserFromEntryId(self, entryId):
        if entryId.startswith("NT User"):
            entryId = entryId[8:]
            start = entryId[0:2]
            if start == "S-":
                # Seems we have a SID from a group, so "skip"
                #return self.__acctGetBySid(entryId)
                return None
            else:
                # Seems we have a Domain USER.
                return None #self.__acctGetByDomain(entryId)
        else:
            # Assume this is a normal user, or default one
            return entryId

    def __transformAclTableToDict(self, store):
        self.env.log.debug("Transform ACL Table to dict (%s)" % id)

        prop = store.OpenProperty(
            mapitags.PR_ACL_TABLE,
            mapi.IID_IExchangeModifyTable,
            0,
            mapi.MAPI_DEFERRED_ERRORS)

        members = dict()
        table = prop.GetTable(0)
        count = table.GetRowCount(0)
        acls = mapi.HrQueryAllRows(table, None, None, None, count)

        for acl in acls:
            members[acl[2][1]] = self.__getLibgroupwareRightsFlag(acl[4][1])
 
        return members
   
    @Command()
    def folderListWithMembers(self, id):

        """ Get a folder List with all Member Acls """
        folderWithMembers = dict()
        #Create a session here to pass to foldetGetMembers
        workingProfile = id.split("/")[1]
        print workingProfile
        #print "Creating MAPI Profile for ", workingProfile
        self._createMapiProfile(workingProfile)
        session = mapi.MAPILogonEx(0,
            workingProfile,
            None,
            mapi.MAPI_EXTENDED | mapi.MAPI_EXPLICIT_PROFILE)

        #get all msgStores of the mapi under the specified folder
        msgStoreList = self.__getFolderSubtreeMsgStores(id, workingProfile, session)

        #walk throug and get the memeberdirct from each of them.
        for folderName, MemberList in msgStoreList.items():
            folderWithMembers[unicode(folderName)] =  self.__transformAclTableToDict(MemberList)
        print folderWithMembers
        return folderWithMembers

    @Command()
    def folderListWithMembers__running(self, id):

        """ Get a folder List with all Member Acls """
        folderWithMembers = dict()
        folders = self.folderList(id)
        #Create a session here to pass to foldetGetMembers
        workingProfile = id.split("/")[1]
        print workingProfile
        #print "Creating MAPI Profile for ", workingProfile
        self._createMapiProfile(workingProfile)
        session = mapi.MAPILogonEx(0,
            workingProfile,
            None,
            mapi.MAPI_EXTENDED | mapi.MAPI_EXPLICIT_PROFILE)

        for folder in folders:
            folderWithMembers[folder] = self.folderGetMembers(folder, session)
        
        return folderWithMembers

    def __getFolderSubtreeMsgStores(self, id, workingProfile = None, session = None):
        if workingProfile == None:
            workingProfile = id.split("/")[1]
        try:
            if session == None:            
                #print "Creating MAPI Profile for ", workingProfile
                self._createMapiProfile(workingProfile)
                session = mapi.MAPILogonEx(0,
                    workingProfile,
                    None,
                    mapi.MAPI_EXTENDED | mapi.MAPI_EXPLICIT_PROFILE)

            # Get the EMS, PF and PST store IDs
            msgStoresTable = session.GetMsgStoresTable(0)

            #self.__get_user_folder(accountId, id, session)
            propTags = [mapitags.PR_PROVIDER_DISPLAY_A,
                mapitags.PR_DISPLAY_NAME_A,
                mapitags.PR_ENTRYID,
                mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID
                ]
            msgStoresRows = mapi.HrQueryAllRows(msgStoresTable, propTags, None, None, 0)
            #print "1 ", msgStoresRows
            
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
                        re.search("^Postf", msgStoreName):
                    msgStoreType = "private"
                    path = "user/" + workingProfile
                    subtreeEIDTag = mapitags.PR_IPM_SUBTREE_ENTRYID
                    print "userFolder"

                #elif (msgStore[0][1] == "Microsoft Exchange Server" or \
                #        "Microsoft Exchange Message Store") and \
                #        msgStore[1][1] == "Public Folders":
                elif msgStore[3][1] != None:
                    #print "Found public folder"
                    msgStoreType = "public"
                    path = "shared/All Public Folders"
                    subtreeEIDTag = mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID
                    print "publicFolder"

                elif msgStore[0][1] == "Personal Folders" and re.search("^Temp", msgStoreName):
                    msgStoreType = "personal"
                    subtreeEIDTag = mapitags.PR_IPM_SUBTREE_ENTRYID
                    print "personalFolder"
                else:
                    continue
                
                msgStore = session.OpenMsgStore(0,
                        msgStoreID,
                        None,
                        mapi.MDB_NO_DIALOG | mapi.MAPI_BEST_ACCESS)
                hr, props = msgStore.GetProps((subtreeEIDTag,), 0)
                subtreeEID = props[0][1]
                subtreeFolder = msgStore.OpenEntry(subtreeEID, None, 0)
                #holde rekursiv den gesuchten msgstore.
                mystore = self.__findSubfolderMsgStoreList(subtreeFolder,
                        subtreeEIDTag, id, workingProfile, path)
                # If the table was not found go ahead
                if mystore == None:
                    continue
            return mystore
        except (Exception), e:
            self.env.log.error("Received Error in __getFolderSubtreeMsgStores", e)
            raise e
        finally:
            self._deleteMapiProfile(workingProfile)
            table = None
            acls = None
            prop = None
            mystore = None
            session = None
            msgStore = None
            subtreeFolderHierarchyRows = None
            subtreeFolderHierarchy = None
            subtreeFolder = None
            # Uninitialise
        return None

    def __workOnFolder(self, id, function, workingProfile = None, session = None):
        if workingProfile == None:
            workingProfile = id.split("/")[1]
        try:
            if session == None:            
                #print "Creating MAPI Profile for ", workingProfile
                self._createMapiProfile(workingProfile)
                session = mapi.MAPILogonEx(0,
                    workingProfile,
                    None,
                    mapi.MAPI_EXTENDED | mapi.MAPI_EXPLICIT_PROFILE)

            # Get the EMS, PF and PST store IDs
            msgStoresTable = session.GetMsgStoresTable(0)

            #self.__get_user_folder(accountId, id, session)
            propTags = [mapitags.PR_PROVIDER_DISPLAY_A,
                mapitags.PR_DISPLAY_NAME_A,
                mapitags.PR_ENTRYID,
                mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID
                ]
            msgStoresRows = mapi.HrQueryAllRows(msgStoresTable, propTags, None, None, 0)
            #print "1 ", msgStoresRows

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
                    #print "Found public folder"
                    msgStoreType = "public"
                    path = "shared/All Public Folders"
                    subtreeEIDTag = mapitags.PR_IPM_PUBLIC_FOLDERS_ENTRYID

                elif msgStore[0][1] == "Personal Folders" and re.search("^Temp", msgStore[1][1]):
                    msgStoreType = "personal"
                    subtreeEIDTag = mapitags.PR_IPM_SUBTREE_ENTRYID

                else:
                    continue

                msgStore = session.OpenMsgStore(0,
                        msgStoreID,
                        None,
                        mapi.MDB_NO_DIALOG | mapi.MAPI_BEST_ACCESS)

                hr, props = msgStore.GetProps((subtreeEIDTag,), 0)
                subtreeEID = props[0][1]
                subtreeFolder = msgStore.OpenEntry(subtreeEID, None, 0)
                
                if (path == id):
                    return function(subtreeFolder)
                #holde rekursiv den gesuchten msgstore.
                mystore = self.__findSubfolderMsgStore(subtreeFolder,
                        subtreeEIDTag, id, workingProfile, path)

                # If the table was not found go ahead
                if mystore == None:
                    continue

                # Execute the working algorithm
                return function(mystore)

        except (Exception), e:
            self.env.log.error("Received Error in _workOnFolder")
            raise e
        finally:
            self._deleteMapiProfile(workingProfile)
            table = None
            acls = None
            prop = None
            mystore = None
            session = None
            msgStore = None
            subtreeFolderHierarchyRows = None
            subtreeFolderHierarchy = None
            subtreeFolder = None
            # Uninitialise
        return None

    @Command()
    def folderSetMembers(self, id, members):
        """ Set members for folder """
        super(MSExchange, self).folderSetMembers(id, members)
        if not self.folderExists(id):
            raise GroupwareNoSuchObject
        # function used as closure
        def transformAclAndPersist(mystore):
            prop = mystore.OpenProperty(
                    mapitags.PR_ACL_TABLE,
                    mapi.IID_IExchangeModifyTable,
                    0,
                    mapi.MAPI_DEFERRED_ERRORS)

            #members = dict()
            table = prop.GetTable(0)
            count = table.GetRowCount(0)
            acls = mapi.HrQueryAllRows(table, None, None, None, count)
            tempDict = {}
            #print acls
            for acl in acls:
                tempDict[acl[2][1]] = 1

            newAclTable = []
            for member in members:
                if member in tempDict:
                    modifierFlag = mapitags.ROW_MODIFY
                else:
                    modifierFlag = mapitags.ROW_ADD
                
                if members[member] == None:
                    flags = 0
                else:
                    flags = members[member]
                
                if member == "Anonym":
                    entryId = -1
                    newAclTable.append((mapitags.ROW_MODIFY, \
                        [
                            (mapitags.PR_MEMBER_ID, entryId),
                            (mapitags.PR_MEMBER_RIGHTS, \
                                self.__getMapiRightsFlag(flags)),
                        ]))
                elif member == "Standard":
                    entryId = 0
                    newAclTable.append((mapitags.ROW_MODIFY, \
                        [
                            (mapitags.PR_MEMBER_ID, entryId),
                            (mapitags.PR_MEMBER_RIGHTS, \
                                self.__getMapiRightsFlag(flags)),
                        ]))
                else:
                    try:
                        try:
                            mapiRightsFlag = self.__getMapiRightsFlag(flags)
                        except GroupwareValue:
                            mapiRightsFlag = 0 

                        entryId = mapiutil.gen_exchange_entry_id(member)
                        newAclTable.append((modifierFlag, \
                            [
                                (mapitags.PR_ENTRYID, a2b_hex(entryId)),
                                (mapitags.PR_MEMBER_RIGHTS, \
                                    self.__getMapiRightsFlag(flags)),
                            ]))
                    except Exception, e:
                        self.env.log.error("Received Error in _workOnFolder while working on aclTable ")
                        raise e

            for acl in acls:
                if acl[2][1].startswith("NT User:S-"):
                    # Should be better to really check if it is a group
                    # instead of assuming that a sid is always a group
                    #print acl
                    
                    newAclTable.append((mapitags.ROW_ADD, \
                        [
                            (mapitags.PR_ENTRYID, \
                                acl[3][1]),
                            (mapitags.PR_MEMBER_RIGHTS, \
                                acl[4][1]),
                        ]))
            prop.ModifyTable(1, newAclTable)
            return True

        #return self.__workOnFolder(id, transformAclAndPersist)
        if id.startswith("shared"):
            accountId = self.env.config.getOption("admin_id", "exchange")
            return self.__workOnFolder(id, transformAclAndPersist, accountId)
        else: 
            return self.__workOnFolder(id, transformAclAndPersist)

    @Command()
    def acctGetComprehensiveUser(self, accountId):
        """
        method to gather a comprehensive dict of data to an specified account 
        to minimize the calls over amqp.
        """
        super(MSExchange, self)._checkAccount(accountId)

        acctData = dict({"primaryMail": self.acctGetPrimaryMailAddress(accountId)})
        #acctData[""] = selfGet (accountId)
        acctData["alternateAddresses"] = self.acctGetAlternateMailAddresses(accountId)
        acctData["forwardingAddresses"] = self.acctGetMailForwardAddresses (accountId)
        acctData["mailLocation"] = self.acctGetLocation(accountId)
        acctData["quota"] = self.acctGetQuota (accountId)
        acctData["mailLimits"] = self.acctGetMailLimit (accountId)
        acctData["vacation"] = self.acctGetOutOfOfficeReply (accountId)
        
        return acctData

    @Command()
    def acctGetFilters(self, accountId):
        """ gathering the Filters via Mapi """
        super(MSExchange, self).acctGetFilters(accountId)

        self._createMapiProfile(accountId)

        session = mapi.MAPILogonEx(0, accountId, None, mapi.MAPI_NEW_SESSION | mapi.MAPI_NO_MAIL)
        
        mapiSimplifier = MapiSimplifier(session)
        inboxFolder = mapiSimplifier.openRecieveFolder()
        
        rulesModifyTable = inboxFolder.OpenProperty(mapitags.PR_RULES_TABLE, mapi.IID_IExchangeModifyTable, 0 , mapi.MAPI_DEFERRED_ERRORS)
        
        gosaRules = []
        table = rulesModifyTable.GetTable(0)
        count =  table.GetRowCount(0)
        mapiRules = mapi.HrQueryAllRows(table, None, None, None, count)
        print mapiRules
        for rule in mapiRules:
            print "#> ", rule
            gosaRule = dict()
            print rule;
            for propValue in rule:
                if propValue[0] == mapitags.PR_RULE_ID:
                    gosaRule['id'] = propValue[1]
                elif propValue[0] == mapitags.PR_RULE_ACTIONS:
                    gosaRule['actions'] = self._decomposeAction(propValue[1], \
                        session)
                elif propValue[0] == mapitags.PR_RULE_CONDITION:
                    #print propValue[1]
                    print "**>", propValue[1]
                    gosaRule["TYPE"], gosaRule['CONDITIONS'] = \
                        MapiRestrictionReader.getFilter( \
                        propValue[1])
        
            gosaRules.append(gosaRule)
        
        inboxFolder = None
        rulesModifyTable = None
        table = None
        mapiSimplifier = None
        session = None

        self._deleteMapiProfile(accountId)
        return gosaRules
        
    def _decomposeAction(self, mapiActions, session):
        actions = []
        mapiSimplifier = MapiSimplifier(session)
        if mapiActions == None:
            return actions
        for mapiAction in mapiActions:
            action = {}

            for key  in mapiAction:
                if key == "acttype":
                    acttype = mapiAction[key]
                    if acttype == 10:
                        action["action"] = "delete"
                    elif acttype == 3:
                        action = {'action': 'reply',\
                            'value': 'this is a message'}
                    elif acttype == 2:
                        action = GosaActionFactory.createCopyFromMapi( \
                            mapiAction, mapiSimplifier)
                    elif acttype == 1:
                        pass
                        action = GosaActionFactory.createMoveFromMapi( \
                            mapiAction, mapiSimplifier)
                    elif acttype == 11:
                        pass
                        action = GosaActionFactory.createMarkAsReadFromMapi()
                    else:
                        mapiSimplifier = None
                    	raise GroupwareValueError(N_("Rule not supported by backend"))
        
            actions.append(action)
        mapiSimplifier = None
        
        return actions

    @Command()
    def acctSetFilters(self, accountId, data):
        """ Set account filter """
        super(MSExchange, self).acctSetFilters(accountId, data)

        self._createMapiProfile(accountId)

        session = mapi.MAPILogonEx(0, accountId, None, mapi.MAPI_NEW_SESSION | mapi.MAPI_NO_MAIL)

        mapiSimplifier = MapiSimplifier(session)
        inboxFolder = mapiSimplifier.openRecieveFolder()


        rulesModifyTable = inboxFolder.OpenProperty(mapitags.PR_RULES_TABLE, mapi.IID_IExchangeModifyTable, 0 , mapi.MAPI_DEFERRED_ERRORS)

        newRuleTable = []

        i = 0
        for filter in copy.deepcopy(data):
            entries = self._createRuleEntries(filter, i, session = session)
            newRuleTable.append((mapitags.ROW_ADD, entries))
            i += 1

        # Replace Rules
        #print "\n Replace... \n" , newRuleTable , "\n ------\n"
        myReturnValue = rulesModifyTable.ModifyTable(1, newRuleTable)

        # Cleanup
        mapiSimplifier = None
        session = None
        
        self._deleteMapiProfile(accountId)
        table = None
        acls = None
        foo = None
        mystore = None
        msgStore = None
        subtreeFolderHierarchyRows = None
        subtreeFolderHierarchy = None
        subtreeFolder = None
        return myReturnValue

    def _createRuleEntries(self, filter, sequence = -1, session = None):
        actions = []
        ruleProvider = "RuleOrganizer2"
        state = mapitags.ST_ENABLED
        #print "\n Entry Action", filter['action'],  " (",filter,")!!!! \n"
        #actionOperator = filter[self.ACTIONS_KEY][0]['action']
        gosaActions = filter["actions"]
        mapiSimplifier = MapiSimplifier(session)
        inboxFolder = mapiSimplifier.openRecieveFolder()
        for action in gosaActions:
            actionOperator = action['action']
            if actionOperator == OP_MOVE:
                #tmp = self._replaceFolderWithUids(session, action)
                actions.append(MapiActionFactory.createMoveAsMapi(action,mapiSimplifier))
            elif actionOperator == OP_COPY:
                #tmp = self._replaceFolderWithUids(session, action)
                actions.append(MapiActionFactory.createCopyAsMapi(action,mapiSimplifier))
            elif actionOperator == OP_REPLY:
                #self._createMessage(filter)
                #session = mapi.MAPILogonEx(0, id, None, mapi.MAPI_NEW_SESSION | mapi.MAPI_NO_MAIL)
                msg = action["value"]
                inboxFolder = mapiSimplifier.openRecieveFolder()
                message = inboxFolder.CreateMessage(None, mapi.MAPI_DEFERRED_ERRORS | mapi.MAPI_ASSOCIATED)
                message.SetProps([(mapitags.PR_BODY_A, msg),
                                  (mapitags.PR_MESSAGE_CLASS,"IPM.Note.Rules.OofTemplate.Microsoft") # Just for OOReply!!!
                                  ])
                KEEP_OPEN_READWRITE = 0x00000002
                FORCE_SAVE = 0x00000004    # save changes and submit
                message.SaveChanges(KEEP_OPEN_READWRITE | FORCE_SAVE)
                entryid = message.GetProps((mapitags.PR_ENTRYID), 0)
                (tag, eid) = entryid[1][0]
                action = filter["actions"][0]
                action["msgEid"] = eid
                actions.append(MapiActionFactory.createReplyAsMapi(action, mapiSimplifier))
            elif actionOperator == OP_OOOREPLY:
                ruleProvider = "MSFT:TDX OOF Rules"
                state |= mapitags.ST_KEEP_OOF_HIST | mapitags.ST_ONLY_WHEN_OOF
                mapiSimplifier = MapiSimplifier(session)
                actions.append(MapiActionFactory.createOofReplyAsMapi(action, mapiSimplifier))
            elif actionOperator == OP_FORWARD:
                actions.append(MapiActionFactory.createForwardAsMapi(action))
            elif actionOperator == OP_DELETE:
                actions.append(MapiActionFactory.createDeleteAsMapi(action))
            elif actionOperator == OP_MARKAS:
                actions.append(MapiActionFactory.createMarkAsReadAsMapi(action))
            else:
                raise GroupwareValueError(N_("Invalid action operator '%s'"), actionOperator)

        restriction = None
        #actionFactory.get(filter['action'])(filter)
        restriction = MapiRestrictionFactory.createRestriction(filter["TYPE"], \
            filter['CONDITIONS'])
        #flags = transformFlags(filter['flags'])
        entries = [(mapitags.PR_RULE_SEQUENCE, sequence),  \
            (mapitags.PR_RULE_PROVIDER, ruleProvider),  \
            (mapitags.PR_RULE_STATE, state), \
            (mapitags.PR_RULE_CONDITION, restriction), \
            #(PR_RULE_USER_FLAGS, 2), \
            (mapitags.PR_RULE_ACTIONS, actions), \
            (mapitags.PR_RULE_NAME, filter['name'])
            ]

        mapiSimplifier = None
            
        return entries

    def _replaceMessageTextWithReplyMessageEid(self, session, filter):
        return filter

    def _searchEidOfMsStoreAndFolder(self, session, searchterm):
        pass



    @Command()
    def acctAddFilter(self, accountId, filter):
        """ Add filter via MApi """
        super(MSExchange, self).acctAddFilter(accountId, filter)

        self._createMapiProfile(accountId)

        session = mapi.MAPILogonEx(0, accountId, None, mapi.MAPI_NEW_SESSION | mapi.MAPI_NO_MAIL)

        myReturnValue = self._addFilter(session, filter)

        # Cleanup
        self._deleteMapiProfile(accountId)
        table = None
        acls = None
        foo = None
        mystore = None
        session = None
        msgStore = None
        subtreeFolderHierarchyRows = None
        subtreeFolderHierarchy = None
        subtreeFolder = None
        return myReturnValue

    def _addFilter(self, session, filter):
        mapiSimplifier = MapiSimplifier(session)
        inboxFolder = mapiSimplifier.openRecieveFolder()
        rulesModifyTable = inboxFolder.OpenProperty(mapitags.PR_RULES_TABLE, mapi.IID_IExchangeModifyTable, 0 , mapi.MAPI_DEFERRED_ERRORS)

        newRuleTable = []

        entries = self._createRuleEntries(filter,0,session = session)
        newRuleTable.append((mapitags.ROW_ADD, entries))
        #print newRuleTable
        # Replace Rules

        rulesModifyTable.ModifyTable(0, newRuleTable)

        mapiSimplifier = None

        return True

    @Command()
    def acctDelFilter(self, accountId, filterId):
        """ Deleting a Filter """
        super(MSExchange, self).acctDelFilter(accountId, filterId)

        self._createMapiProfile(accountId)

        session = mapi.MAPILogonEx(0, accountId, None, mapi.MAPI_NEW_SESSION | mapi.MAPI_NO_MAIL)

        mapiSimplifier = MapiSimplifier(session)
        inboxFolder = mapiSimplifier.openRecieveFolder()
        
        rulesModifyTable = inboxFolder.OpenProperty(mapitags.PR_RULES_TABLE, mapi.IID_IExchangeModifyTable, 0 , mapi.MAPI_DEFERRED_ERRORS)

        ruleModify = []
        table = rulesModifyTable.GetTable(0)
        count =  table.GetRowCount(0)
        mapiRules = mapi.HrQueryAllRows(table, None, None, None, count)
        ruleModify = [(mapitags.ROW_REMOVE,  \
                [(mapitags.PR_RULE_ID, filterId)])] \

        rulesModifyTable.ModifyTable(0, ruleModify)
        self._deleteMapiProfile(accountId)

        mapiSimplifier = None
        return True



    @Command()
    def folderAddMember(self, id, accountId, permission):
        """ Add member to folder """
        if not self.folderExists(id):
            raise GroupwareNoSuchObject

        if not self.acctExists(accountId):
            raise GroupwareNoSuchObject

        def addNewAclEntryToFolder(mystore):
            # Could replace the exist test before, cause this method doed a AD Query.
            data = mapiutil.gen_exchange_entry_id(accountId)
            prop = mystore.OpenProperty(mapitags.PR_ACL_TABLE,
                    mapi.IID_IExchangeModifyTable,
                    0,
                    mapi.MAPI_DEFERRED_ERRORS)

            newacl = [(
                mapitags.ROW_ADD,
                [
                    (mapitags.PR_ENTRYID,a2b_hex(data)),
                    (mapitags.PR_MEMBER_RIGHTS, self.__getMapiRightsFlag(permission))]
                )]

            prop.ModifyTable(0, newacl)

            return True
        if id.startswith("shared"):
            return self.__workOnFolder(id, addNewAclEntryToFolder, accountId)
        else: 
            return self.__workOnFolder(id, addNewAclEntryToFolder)


    def __getMapiRightsFlag(self, libgroupwareRightsFlag):
        # Todo: Fehler muss hier geworfen werden, wenn eine Falsch signatur geschickt wird.
        if libgroupwareRightsFlag in self._mapiToLibGroupwareRightsMap:
            return self._mapiToLibGroupwareRightsMap[libgroupwareRightsFlag]
        else:
            raise GroupwareValueError(N_("AccessRightsflag cannot be mapped to Mapi rights"), libgroupwareRightsFlag)

    def __getLibgroupwareRightsFlag(self, mapiRightsFlag):
        for flag in self._mapiToLibGroupwareRightsMap:
            if mapiRightsFlag in self._mapiToLibGroupwareRightsMap:
            #if self._mapiToLibGroupwareRightsMap[flag] == mapiRightsFlag:
                return flag
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
   
    def __findSubfolderMsgStoreList(self, msgStore, subtreeEIDTag, id, workingProfile, path):
        subtreeFolderHierarchy = msgStore.GetHierarchyTable(0)
        MsgStoreList = dict()        
        # Call the IMAPITable::QueryRows method to list the folders in the top-level folder.
        subtreeFolderHierarchyRows = mapi.HrQueryAllRows(
                subtreeFolderHierarchy,
                [mapitags.PR_DISPLAY_NAME, mapitags.PR_ENTRYID],
                None, None, 0)

        for row in subtreeFolderHierarchyRows:
            #self.env.log.debug("Checking "+ path +"/"+ row[0][1])
            currentPath = path + "/"  + row[0][1]
            if currentPath.startswith(id):
                
                store = msgStore.OpenEntry(row[1][1], None, 0)
                #append the current folder
                MsgStoreList[currentPath] = store
                #recursion - append all subfolders
                subStores = self.__findSubfolderMsgStoreList(
                        store,
                        subtreeEIDTag,
                        id, workingProfile,
                        currentPath)
                if subStores != None:
                    MsgStoreList.update(subStores)
                    #MsgStoreList.append(subStores)
                #self.env.log.debug("Found subfolder: " + path + "/"  + row[0][1])
                #return MsgStoreList 

            elif id.startswith(currentPath):
                store = msgStore.OpenEntry(row[1][1], None, 0)
                sub_store = self.__findSubfolderMsgStoreList(
                        store,
                        subtreeEIDTag,
                        id, workingProfile,
                        path + "/" + row[0][1])

                if sub_store != None:
                    return sub_store

        return MsgStoreList

    @Command()
    def folderDelMember(self, id, accountId):
        """ Remove member from folder """

        if not self.folderExists(id):
            raise GroupwareNoSuchObject

        if not self.acctExists(accountId):
            raise GroupwareNoSuchObject

        def createRemoveTable(mystore):
            prop = mystore.OpenProperty(mapitags.PR_ACL_TABLE, mapi.IID_IExchangeModifyTable, 0 , mapi.MAPI_DEFERRED_ERRORS)
            table = prop.GetTable(0)
            count =  table.GetRowCount(0)
            acls = mapi.HrQueryAllRows(table, None, None, None, count)
            count = 0
            for acl in acls:
                count = count + 1
                if acl[2][1] == accountId:
                    newacl = [(mapitags.ROW_REMOVE, [(mapitags.PR_MEMBER_ID, acl[1][1])])]
                    prop.ModifyTable(0, newacl)
                    return True

        #return self.__workOnFolder(id, createRemoveTable)
        if id.startswith("shared"):
            return self.__workOnFolder(id, createRemoveTable, accountId)
        else: 
            return self.__workOnFolder(id, createRemoveTable)



    @Command()
    def mailAddressExists(self, address):
        """ Check if mail address already exists """
        base = ad.AD_object("LDAP://" + self.__baseDN)
        for obj in base.search("proxyAddresses='*'"):
            for addr in [
                    a[5:] for a in obj.proxyAddresses if a.lower().startswith('smtp:')
                ]:
                if addr == address:
                    return True

        return False

    def __is_domain_admin(self):
        userName = win32api.GetUserName()
        user = ad.find_user(userName)
        groups = user.memberOf

        for grp in groups:
            sid = win32security.ConvertSidToStringSid(grp.objectSid)
            if sid.endswith("512"):
                return True

        return False

    def __get_user_folders(self, id, server = None, root = None, session = None, path = ""):
        last_return = False

        if not server:
            ad_obj = ad.find_user(id)
            ad_obj.GetInfo()
            server = ad_obj.Get("msExchHomeServerName").split("=")[-1].lower()

        if not session:
            cwd = os.getcwd()
            session = win32com.client.Dispatch("MAPI.Session")
            session.Logon('', '', False, True, True, True, server + '\n' + id)
        if not root:
            root = session.InfoStores
            last_return = True

        root_path = path
        result = []

        #for store in root:
        for i in range(1,root.Count+1):
            store = root.Item(i)
            # Skip public folders
            if last_return:
                #skip all public folders - this can be determined by the following mapitag.
                owner = self.__getMapitagOfInfostore(store, mapitags.PR_RESOURCE_FLAGS)
                # If the second last digit of the FLAG Mask is 0 (bitwise and)
                # the folder is a shared folder
                if not int(owner) & 2:
                    continue
                result.append("user/" + id)
            else:
                if self.is_ascii(store.Name):
                    name = store.Name.encode('utf-8')
                else:
                    name = store.Name
                #name = store.Name.encode('utf-8')
                path = root_path + "/" + name
                result.append("user/" + id + path)
            try:
              result.extend(self.__get_user_folders(id, server = server, root = store.RootFolder.Folders, session = session, path = path))
            # TODO: get exactly the exception her which could be thrown by store.RootFolder.Folders!!!
            except:
                try:
                    result.extend(self.__get_user_folders(id, server = server, root = store.Folders, session = session, path = path))
                except:
                    self.env.log.error("store.RootFolder.Folders -id" + id + "-server" + server + "-path" + path)
        # Cleanup
        if last_return:
            session.Logoff()
            os.chdir(cwd)

        return result

    def __get_global_folders(self, server = None, root = None, session = None, path = ""):
        last_return = False

        if not server:
            server = platform.node()

        if not session:
            session = win32com.client.Dispatch("MAPI.Session")
            """
               TODO: remove fixed profile here and get a global profile.
            """
            #session.Logon('', '', False, True, True, True, server + '\n' + 'testhorst6')
            #RUNNING - session.Logon('', '', False, True, True, True, server + '\n' + 'mtestUserinC')
            session.Logon('', '', False, True, True, True, server + '\n' + "Administrator")
            cwd = os.getcwd()

        if not root:
            root = session.InfoStores
            last_return = True

        root_path = path
        result = []

        #for store in root:
        for i in range(1,root.Count+1):
            store = root.Item(i)
            # Skip public folders
            if last_return:
                allFields = store.Fields
                #skip all public folders - this can be determined by the following mapitag.
                owner = self.__getMapitagOfInfostore(store, mapitags.PR_RESOURCE_FLAGS)
                # If the second last digit of the FLAG Mask is 0 (bitwise and)
                # the folder is a shared folder
                if int(owner) & 2:
                   continue
            else:
                name = store.Name.encode('utf-8')
                path = root_path + "/" + name
                result.append("shared" + path)

            try:
                result.extend(self.__get_global_folders(server, root=store.RootFolder.Folders, session=session, path = path))
            except:
                try:
                    result.extend(self.__get_global_folders(server, root=store.Folders, session=session, path=path))
                except Exception, e:
                    self.env.log.debug("store.Folders threw exception while getting global folders:", e)

        # Cleanup
        if last_return:
            session.Logoff()
            os.chdir(cwd)

        return result

    def __get_user_quota(self, server, id, root=None, session=None):
        last_return = False
        quota = 0

        if not session:
            cwd = os.getcwd()
            session = win32com.client.Dispatch("MAPI.Session")
            session.Logon('', '', False, True, True, True, server + '\n' + id)

        if not root:
            root = session.InfoStores
            last_return = True

        for i in range(1,root.Count+1):
            store = root.Item(i)

            # Skip public folders not owned by us
            if last_return:
                allFields = store.Fields
                for j in range(1,allFields.Count+1):
                    myfoo = allFields.Item(j)
                    if myfoo.ID == mapitags.PR_RESOURCE_FLAGS:
                        owner = myfoo.Value
                        break
                    if myfoo.ID == mapitags.PR_MESSAGE_SIZE:
                        storeQuota = myfoo.Value
                        break
                if not int(owner) & 2:
                   continue

            # Add quota usage
            try:
                quota += int(storeQuota)
            except:
                pass

            try:
                quota += self.__get_user_quota(server, id, root = store.RootFolder.Folders, session = session)
            except:
                quota += self.__get_user_quota(server, id, root = store.Folders, session = session)

        # Cleanup
        if last_return:
            session.Logoff()
            os.chdir(cwd)
            return float(quota / 1000)

        return quota

    def __getMapitagOfInfostore(self, InfoStore, mapitag):
        mapitagValue = None
        try:
            iStoreFields = InfoStore.Fields
        except Exception, e:
            raise TypeError(N_("Failed to get infostore fields: %s"), str(e))

        for j in range(1,iStoreFields.Count+1):
            curField = iStoreFields.Item(j)
            #print "ID: ",myfoo.ID, "; Name:", myfoo.Name, "; Type:", myfoo.Type, "; Value:", myfoo.Value
            if curField.ID == mapitags.PR_RESOURCE_FLAGS:
                mapitagValue = curField.Value
                break
        return mapitagValue

    def __get_folder(self, id, server=None, root=None, session=None, path=None):
        last_return = False
        fetchPublicFoldersEnabled = False
        # Evaluate server
        if not server:
            if id.startswith("user/"):
                ad_user = ad.find_user(id.split("/")[1])
                ad_user.GetInfo()
                server = ad_user.Get("msExchHomeServerName").split("=")[-1].lower()
            else:
                server = platform.node()

        if not path:
            cwd = os.getcwd()
            session = win32com.client.Dispatch("MAPI.Session")

            if id.startswith("user/"):
                user = id.split("/")[1]
                path = "user/" + user
                session.Logon('', '', False, True, True, True, server + '\n' + user)
            else:
                path = "shared"
                session.Logon('', '', False, True, True, True, server + '\nAdministrator')
                fetchPublicFoldersEnabled = True

        if not root:
            root = session.InfoStores
            last_return = True

        root_path = path
        result = None

        for i in range(1,root.Count+1):
            store = root.Item(i)
            owner = 0
            # Skip public folders
            # TODO Refactor this part

            """
            want to get public folders too
            """

            if last_return and not fetchPublicFoldersEnabled:
                # try to determine if the folder is a public folder
                owner = self.__getMapitagOfInfostore(store, mapitags.PR_RESOURCE_FLAGS)
                # if so continue with the next InfoStore
                if not int(owner) & 2:
                    continue

            if path == id:
                return store
            if not last_return:
                name = store.Name.encode('utf-8')
                path = root_path + "/" + name
            # If we're on the wrong track, go ahead
            if not id.startswith(path):
                continue
            if path == id:
                return store
            try:
                result = self.__get_folder(id, server = server,
                        root = store.RootFolder.Folders,
                        session = session, path = path)
            except Exception, e:
                try:
                    result = self.__get_folder(id, server = server,
                        root = store.Folders, session = session, path = path)

                except Exception, e:
                    self.env.log.error("cannot open infostore %s" % (id + path))


            # Go ahead with a possible result
            if result:
                return result

        # Cleanup
        if last_return:
            session.Logoff()
            os.chdir(cwd)

        return result

    def _deleteMapiProfile(self, profileName):
        """
        delete a mapi profile with the profile name "pofileName"
        this method throws no error where the given profile does not exist.
        Please call _mapiProfileExists in advance.

        @type pofileName: string
        @param pofileName: name of the profile
        """
        # Initialize
        #mapi.MAPIInitialize((mapi.MAPI_INIT_VERSION, mapi.MAPI_MULTITHREAD_NOTIFICATIONS))

        # Get the handle to administer the profiles
        profileAdmin = mapi.MAPIAdminProfiles(0)

        # Get the current profiles
        profileTable = profileAdmin.GetProfileTable(0)
        profileRows = mapi.HrQueryAllRows(profileTable,
                [mapitags.PR_DISPLAY_NAME_A], None, None, 0)

        # Delete the profile if it already exists
        if filter(lambda p: p[0][1] == profileName, profileRows):
            result = profileAdmin.DeleteProfile(profileName, 0)

    def _createMapiProfile(self, profileName):
        """
        create a mapi profile with the profile name "pofileName"

        @type pofileName: string
        @param pofileName: name of the profile
        """
        # Initialize
        #initOk = mapi.MAPIInitialize((None))
        """
        if not initOk:
            #bale out since the mapi was not initialized
            self.env.log.error("initializing exchange groupware plugin")
            raise GroupwareError("MAPI was not initialized.")
        """
        # Get the handle to administer the profiles
        profileAdmin = mapi.MAPIAdminProfiles(0)
        profileAdmin.CreateProfile(profileName, None, 0, 0)
        # Administer the profile services
        serviceAdmin = profileAdmin.AdminServices(profileName, None, 0, 0)

        serviceAdmin.CreateMsgService('MSEMS', None, 0, 0)    # Add an Exchange service
        #serviceAdmin.CreateMsgService('MSPST MS', None, 0, 0) # Add a .pst file

        # Get the service table - looking for service IDs
        msgServiceTable = serviceAdmin.GetMsgServiceTable(0)
        msgServiceRows = mapi.HrQueryAllRows(msgServiceTable, [mapitags.PR_SERVICE_UID, mapitags.PR_SERVICE_NAME], None, None, 0)

        # Get the service ID of the MSEMS service (first)
        serviceUID = msgServiceRows[0][0][1]
        serviceUID = pythoncom.MakeIID(serviceUID, 1)

        # Configure the Exchange Service
        #propsTuple = ((mapitags.PR_PROFILE_UNRESOLVED_NAME, "USER"),(mapitags.PR_PROFILE_UNRESOLVED_SERVER, "SERVER"))
        propsTuple = ((mapitags.PR_PROFILE_UNRESOLVED_SERVER, platform.node()), (mapitags.PR_PROFILE_UNRESOLVED_NAME, profileName))

        serviceAdmin.ConfigureMsgService(serviceUID, 0, 0, propsTuple)

        # Get the service ID of the MS PST service (last)
        #serviceUID = msgServiceRows[-1][0][1]
        #serviceUID = pythoncom.MakeIID(serviceUID, 1)

        # Configure the .pst file
        #PR_PST_PATH = int(0x6700001E) # This tag is not defined in mapitags?
        #propsTuple = ((mapitags.PR_DISPLAY_NAME_A, "Temp"), (PR_PST_PATH, r"c:\temp.pst"))
        #serviceAdmin.ConfigureMsgService(serviceUID, 0, 0, propsTuple)3

    def _mapiProfileExists(self, profileName):
        """
        Determine the existance of the profile "pofileName"

        @type pofileName: string
        @param pofileName: name of the profile

        @rtype: bool
        @return: True when name exists, False on failure
        """


        # Initialize
        #initOk = mapi.MAPIInitialize((mapi.MAPI_INIT_VERSION, mapi.MAPI_MULTITHREAD_NOTIFICATIONS))
        """
        if not initOk:
            #bale out since the mapi was not initialized
            self.env.log.error("initializing exchange groupware plugin")
            raise GroupwareError("MAPI was not initialized.")
        """
        # Get the handle to administer the profiles
        profileAdmin = mapi.MAPIAdminProfiles(0)

        # Get the profile Table and check the names for a match.
        profileTable = profileAdmin.GetProfileTable(0)
        profileRows = mapi.HrQueryAllRows(profileTable,
                [mapitags.PR_DISPLAY_NAME_A], None, None, 0)

        # Check if there's a profile 4with this name
        return bool(filter(lambda p: p[0][1] == profileName, profileRows))

    def _imapConnection(self, id, password):
        """
        As a workaround for imap access we need to connect to the exchange account once to get
        the necessary access rights set automaitcally.
        """
        # Evaluate server
        ad_user = ad.find_user(id)
        ad_user.GetInfo()
        server = ad_user.Get("msExchHomeServerName").split("=")[-1].lower()

        connection = imaplib.IMAP4(server)
        success = connection.login(id, password)
        connection.logout

    def is_ascii(self, str):
        return all(ord(c)<128 for c in str)
        #try:
        #    str.decode("utf-8")
        #    return true
        #except UnicodeDecodeError:
        #    return false

#TODO: remove me
def dump(obj):
    '''return a printable representation of an object for debugging'''
    newobj=obj
    if '__dict__' in dir(obj):
        newobj=obj.__dict__
        if ' object at ' in str(obj) and not newobj.has_key('__type__'):
            newobj['__type__']=str(obj)
        for attr in newobj:
            newobj[attr]=dump(newobj[attr])
        return newobj


