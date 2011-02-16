# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: base.py 1380 2010-11-19 12:10:31Z hzerres $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
import re
import inspect
import gettext
from util import isMailAddress
from pkg_resources import resource_filename
from gosa.common.utils import N_

# Include locales
t = gettext.translation('messages', resource_filename("libgroupware", "locale"),
        fallback=True)
_ = t.ugettext

# Access constants
LOOKUP = 2 ** 0
READ = 2 ** 1
STATUS = 2 ** 2
WRITE = 2 ** 3
INSERT = 2 ** 4
POST = 2 ** 5
CREATE = 2 ** 6
DELETE = 2 ** 7
ADMINISTRATE = 2 ** 8

# Access constant shortcuts
RIGHTS_NONE = 0
RIGHTS_READ = LOOKUP & READ & STATUS
RIGHTS_POST = RIGHTS_READ & POST
RIGHTS_APPEND = RIGHTS_POST & INSERT
RIGHTS_WRITE = RIGHTS_APPEND & WRITE & CREATE & DELETE
RIGHTS_ALL = RIGHTS_WRITE & ADMINISTRATE

# Account facettes
SMTP = 2 ** 0
SMTPS = 2 ** 1
IMAP = 2 ** 2
IMAPS = 2 ** 3
POP = 2 ** 4
POPS = 2 ** 5
HTTP = 2 ** 6

# Account status
ACTIVE = 2 ** 0
INACTIVE = 2 ** 1
PENDING = 2 ** 2
ERROR = 2 ** 3

# Action types
OP_MOVE = 'move to'
OP_COPY = 'copy to'
OP_FORWARD = 'forward to'
OP_MARKAS = 'mark as'
OP_DELETE = 'delete'
OP_REPLY = 'reply'
OP_OOOREPLY = 'oooreply'


class GroupwareValueError(Exception):
    """
    Exception should be thrown if i.e. a mail address or an id
    does not match the requirements.
    """
    pass


class GroupwareObjectAlreadyExists(Exception):
    """
    Exception should be thrown if i.e. an object exists during
    the try to create it.
    """
    pass


class GroupwareNoSuchObject(Exception):
    """
    Exception should be thrown if i.e. an object is accessed but
    does not exists
    """
    pass

class GroupwareTimeout(Exception):
    """
    Exception should be thrown if an action (i.e. backend communication)
    lasts too long.
    """
    pass


class GroupwareError(Exception):
    """
    Exception should be thrown in generic error cases.
    """
    pass


class Groupware(object):
    """
    This is the groupware interface class. It defines all relevant methods
    needed to interact with any groupware. Implementations of this interface
    should implement as many methods as possible.
    """

    _supportedProperties = {}

    def getCapabilities(self):
        """
        getCapabilities lists all class methods that do not end with
        a "pass" clause. A GUI can use this information to see what
        functionality is implemented.

        @rtype: dict
        @return: dictionary containing method name and a bool "implemented"
                 flag
        """
        caps = {}
        methods = inspect.getmembers(self, lambda x: inspect.ismethod(x))

        # Check which functions end with "pass". These are not implemented.
        for name, ob in methods:
            if name == 'getCapabilities' or name.startswith('_'):
                continue
            caps[name] = inspect.getsourcelines(ob)[0][-1].strip() != "pass"

        return caps

    @staticmethod
    def getName(self):
        """
        Get the name of the current groupware implementation.

        @rtype: string
        @return: Name of the groupware implementation
        """
        return None

    def getMailboxLocations(self):
        """
        Get a list of all available mailbox locations.

        @rtype: list
        @return: list of all mailbox locations
        """
        pass

    def acctList(self, rdn=None):
        """
        Get a list of all known groupware accounts.

        @type rdn: string
        @param rdn: optional location for LDAP like storage

        @rtype: list
        @return: list of all groupware account id's
        """
        pass

    def acctExists(self, id):
        """
        Check if the account exists somewhere.

        @type id: string
        @param id: account id

        @rtype: bool
        @return: True if exists, else False
        """
        pass

    def acctAdd(self, id, address, location=None, rdn=None):
        """
        Add the specified account including the initial mail address to
        the groupware subsystem.

        @type id: string
        @param id: unique account id

        @type sn: string
        @param sn: Accounts surename

        @type givenName: string
        @param givenName: Accounts given name

        @type address: string
        @param address: mail address

        @type location: string
        @param location: location which will host the mailbox

        @type rdn: string
        @param rdn: optional location for LDAP like storage

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        pass

    def acctGetComprehensiveUser(self, id):
        """
        TODO: To be commented 
        """
        pass;

    def acctSetLocation(self, id, location):
        """
        Set the accounts mailbox location. May migrate the account
        to another location (same backend).

        @type id: string
        @param id: unique account id

        @type location: string
        @param location: location which will host the mailbox

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetLocation(self, id):
        """
        Retrieve the accounts mailbox location.

        @type id: string
        @param id: unique account id

        @rtype: string
        @return: location hosting the mailbox
        """
        self._checkAccount(id)
        pass

    def acctSetEnabled(self, id, enable):
        """
        Enable or disable account.

        @type id: string
        @param id: unique account id

        @type enable: bool
        @param enable: True if account should be enabled

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetStatus(self, id):
        """
        Retrieve the account status.

        @type id: string
        @param id: unique account id

        @rtype: dict
        @return: dictionary with the following keys:

            'status':  int

                One of ACTIVE/INACTIVE/PENDING/ERROR

            'message': string

                In case of PENDING or ERROR, an error message can be
                placed here.
        """
        self._checkAccount(id)
        pass

    def acctDel(self, id, purge=False):
        """
        Delete the specified account id from the groupware subsystem.

        @type id: string
        @param id: unique account id

        @type purge: bool
        @param purge: determine if the mailbox should be removed

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetProperties(self, id):
        """
        Get account property flags, indicating what services the account is
        allowed to use.

        @type id: string
        @param id: unique account id

        @rtype: int
        @return: and combination of HTTP/SMTP/SMTPS/IMAP/IMAPS/POP/POPS
        """
        self._checkAccount(id)
        pass

    def acctGetSupportedProperties(self):
        """
        Return dictionary of supported properties that can be set for
        the specified account.

        @rtype: dict
        @return: Dictionary with the following keys:
            {
                property: {
                    'default': True/False,
                    'read-only': True/False
                },
                ...
            }
        """
        return self._supportedProperties

    def acctSetProperties(self, id, props):
        """
        Set account property flags, indicating what services the account is
        allowed to use.

        @type id: string
        @param id: unique account id

        @type props: int
        @param props: and combination of HTTP/SMTP/SMTPS/IMAP/IMAPS/POP/POPS

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)

        # Check if the supplied properties are supported
        for prop in [HTTP, SMTP, SMTPS, IMAP, IMAPS, POP, POPS]:
            # Ignore for property check
            if not prop in self._supportedProperties:
                raise GroupwareValueError(N_("Backend does not provide property support information"))

            # Read-only and non default value?
            if self._supportedProperties[prop]['read-only'] and \
                bool(props & prop) != self._supportedProperties[prop]['default']:
                #TODO: debug message to symbolic string
                raise GroupwareValueError(N_("Property %d is read-only and cannot be changed"), prop)
        pass

    def acctGetPrimaryMailAddress(self, id):
        """
        Read the primary mail address of the supplied account id.

        @type id: string
        @param id: unique account id

        @rtype: string
        @return: mail address
        """
        self._checkAccount(id)
        pass

    def acctSetPrimaryMailAddress(self, id, address):
        """
        Set the primary mail address for the supplied account id.

        @type id: string
        @param id: unique account id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkAccount(id)
        pass

    def acctGetAlternateMailAddresses(self, id):
        """
        Read the list of alternate mail addresses for the supplied account
        into a list.

        @type id: string
        @param id: unique account id

        @rtype: list
        @return: list of mail addresses
        """
        self._checkAccount(id)
        pass

    def acctSetAlternateMailAddresses(self, id, addresses):
        """
        Sets a list of alternate mail addresses for the supplied account. This
        replaces all existing alternate addresses for this account.

        @type id: string
        @param id: unique account id

        @type addresses: list
        @param addresses: list of addresses

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        for address in addresses:
            self._checkMail(address)
        pass

    def acctAddAlternateMailAddress(self, id, address):
        """
        Add a single mail address to the list of alternate mail addresses for
        the supplied account.

        @type id: string
        @param id: unique account id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkAccount(id)
        pass

    def acctDelAlternateMailAddress(self, id, address):
        """
        Remove a single mail address from the list of alternate mail addresses
        for the supplied account.

        @type id: string
        @param id: unique account id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkAccount(id)
        pass

    def acctGetMailForwardAddresses(self, id):
        """
        Read the list of forward mail addresses for the supplied account
        into a dictionary of address/redirect flag mappings. The redirect
        flag is true if the mail gets redirected instead of forwarded.

        @type id: string
        @param id: unique account id

        @rtype: dict
        @return: dict of mail address / redirect flag entries
        """
        self._checkAccount(id)
        pass

    def acctSetMailForwardAddresses(self, id, addresses):
        """
        Sets a dictionary of forward mail addresses / redirect flag entries
        for the supplied account. This replaces all existing forward addresses
        for this account..

        @type id: string
        @param id: unique account id

        @type addresses: dict
        @param addresses: dict of mail address / redirect flag entries

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        for address in addresses:
            self._checkMail(address)
        pass

    def acctAddMailForwardAddress(self, id, address, redirect):
        """
        Add a single mail address / redirect flag to the list of forward
        addresses for the supplied account.

        @type id: string
        @param id: unique account id

        @type address: string
        @param address: address to forward to

        @type redirect: bool
        @param redirect: redirect (True) or forward (False)

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkAccount(id)
        pass

    def acctDelMailForwardAddress(self, id, address):
        """
        Remove a single mail address from the list of forward mail addresses
        for the supplied account.

        @type id: string
        @param id: unique account id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkAccount(id)
        pass

    def acctGetOutOfOfficeReply(self, id):
        """
        Returns a dictionary for the out of office reply mechanism.

        @type id: string
        @param id: unique account id

        @rtype: dict
        @return: Dictionary for the out of office reply mechanism.
            It consists of these keys:

            'message': string

                Unicode string containing the out of office
                message. 'None' if there is no message defined.

            'begin': unix timestamp

                Timestamp in timezone Z which indicates when to start
                returning the out of office message.

            'end': unix timestamp

                Timestamp in timezone Z which indicates when to stop
                returning the out of office message.
        """
        self._checkAccount(id)
        pass

    def acctSetOutOfOfficeReply(self, id, msg, begin=None, end=None):
        """
        Set or disable the out of office reply message.

        @type id: string
        @param id: unique account id

        @type msg: string
        @param msg: Unicode string containing the out of office
            message. 'None' if the message should be disabled.

        @type begin: int
        @param begin: Timestamp in timezone Z which indicates when to
            start returning the out of office message.

        @type end: int
        @param end: Timestamp in timezone Z which indicates when to
            stop returning the out of office message.

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetQuota(self, id):
        """
        Returns a dictionary containing quota information for the
        specified account id.

        @type id: string
        @param id: unique account id

        @rtype: dict
        @return: dictionary with these keys:
            'warn_limit': int

                mailbox size in KB where the server will start to warn
                about full mailboxes. None: disabled

            'send_limit': int

                mailbox size in KB where the server will refuse to send
                mails for that account. None: disabled

            'hard_limit': int

                mailbox size in KB where the server will refuse to send
                and receive mails for that account. None: disabled

            'hold': int

                number of days messages are kept before getting
                removed automatically. None: disabled

            'usage': int

                current quota utilization in KB
        """
        self._checkAccount(id)
        pass

    def acctSetQuota(self, id, warn_limit, send_limit, hard_limit, hold = None):
        """
        Specify the quota settings for the supplied account.

        @type id: string
        @param id: unique account id

        @type warn_limit: int
        @param warn_limit: mailbox size in KB where the server will
            start to warn about full mailboxes. None disables warnings.

        @type send_limit: int
        @param send_limit: mailbox size in KB where the server will
            refuse to send mails for that account. None disables
            the send limit.

        @type hard_limit: int
        @param hard_limit: mailbox size in KB where the server will
            refuse to send and receive mails for that account. None
            disables the hard limit.

        @type hold: int
        @param hold: number of days messages are kept before getting
            removed automatically. None disables messages removal.

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetMailLimit(self, id):
        """
        Get the per mail limit for the supplied account id.

        @type id: string
        @param id: unique account id

        @rtype: dict
        @return: dictionary containing these keys:

            'send': int

                Contains the size limit in KB for outgoing mails sent
                by this account.

            'receive': int

                Contains the size limit in KB for incoming mails sent
                to this account.
        """
        self._checkAccount(id)
        pass

    def acctSetMailLimit(self, id, send=None, receive=None):
        """
        Set the per mail limit for the supplied account id.

        @type id: string
        @param id: unique account id

        @type send: int
        @param send: size limit in KB for outgoing mails

        @type receive: int
        @param receive: size limit in KB for incoming mails

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctGetFilters(self, id):
        """
        Get the list of defined filters for the supplied account id.

        @type id: string
        @param id: unique account id

        @rtype: list
        @return: list of dictionaries describing filters containing these keys:

            'type' : string

                The type determines if the conditions of the current
                filter should be combined with AND or OR logic. Valid
                values are "AND" and "OR".

            'condition' : list

                List of conditions that describe the 'when' the filter
                will perform the defined actions. One condition is a
                dictionary with the keys 'field', 'match' and 'value'.

                'field' contains a mail header keyword or one of 'size' and
                'body'.

                'match' contains one of 'is', 'is not', 'equal', 'not equal',
                'empty', 'not empty', 'contains', 'contains not',
                'greater' and 'less'.

                'value' contains the value to be matched.


            'action' : list

                List of actions that must be executed if the conditions
                match depending on 'type'. An action is a dictionary
                containing the keys 'action' and 'value'.

                'action' is one of 'move', 'copy', 'forward', 'mark',
                'delete' and 'reply'.

                'value' depends on action. 'move' and 'copy' take a list
                valid folders. 'forward' takes a list of mail addresses.
                'mark' takes one of 'read', 'unread', 'delete' has no
                value and 'reply' takes a reply mail-text.
        """
        self._checkAccount(id)
        pass

    def acctSetFilters(self, id, data):
        """
        Set a list of filters for the supplied account id. This
        replaces all existing filters for the account.

        @type id: string
        @param id: unique account id

        @type data: list
        @param data: list of filter definitions, format see acctGetFilters.

        @rtype: list
        @return: list of filters
        """
        self._checkAccount(id)
        pass

    def acctAddFilter(self, id, filter):
        """
        Add a single filter to the supplied account id.

        @type id: string
        @param id: unique account id

        @type filtr: string
        @param filtr: filter description, see acctGetFilters

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def acctDelFilter(self, id, filterId):
        """
        Remove a single filter from the supplied account id.

        @type id: string
        @param id: unique account id

        @type filterId: int
        @param filterId: id of the filter, retrievable by acctGetFilters()

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkAccount(id)
        pass

    def distList(self, rdn=None):
        """
        Get a list of all known groupware distribution lists.

        @type rdn: string
        @param rdn: optional location for LDAP like storage

        @rtype: dict
        @return: dict of all groupware distribution id's and
                 their primary mail address.
        """
        pass

    def distExists(self, id):
        """
        Check if the distribution list exists somewhere.

        @type id: string
        @param id: distribution list id

        @rtype: bool
        @return: True if exists, else False
        """
        pass

    def distAdd(self, id, address, location=None, rdn=None):
        """
        Add the specified distribution list including the initial mail address
        to the groupware subsystem.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @type location: string
        @param location: where to add the distribution list

        @type rdn: string
        @param rdn: optional location for LDAP like storage

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)

        if self.distExists(id):
            #TRANSLATOR: "Distribution list object 'distlist name' already exists"
            raise GroupwareValueError(N_("Distribution list object '%s' already exists"), id)
        pass

    def distGetStatus(self, id):
        """
        Retrieve the distribution list status.

        @type id: string
        @param id: unique dist list id

        @rtype: dict
        @return: dictionary with the following keys:

            'status':  int

                One of ACTIVE/INACTIVE/PENDING/ERROR

            'message': string

                In case of PENDING or ERROR, an error message can be
                placed here.
        """
        self._checkDist(id)
        pass

    def distRename(self, id, new_id, rdn=None):
        """
        Add the specified distribution list including the initial mail address
        to the groupware subsystem.

        @type id: string
        @param id: unique distribution list id

        @type new_id: string
        @param new_id: new unique distribution list id

        @type rdn: string
        @param rdn: new rdn in case of moves

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        if self.distExists(new_id):
            raise GroupwareValueError(N_("Distribution list object '%s' already exists"), new_id)
        pass

    def distDel(self, id):
        """
        Delete the specified distribution list from the groupware subsystem.

        @type id: string
        @param id: unique distribution list id

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        pass

    def distGetPrimaryMailAddress(self, id):
        """
        Read the primary mail address of the supplied distribution list id.

        @type id: string
        @param id: unique distribution list id

        @rtype: string
        @return: mail address
        """
        self._checkDist(id)
        pass

    def distSetPrimaryMailAddress(self, id, address):
        """
        Set the primary mail address for the supplied distribution list id.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        self._checkMail(address)
        pass

    def distGetAlternateMailAddresses(self, id):
        """
        Read the list of alternate mail addresses for the supplied distribution
        list into a list.

        @type id: string
        @param id: unique distribution list id

        @rtype: list
        @return: list of mail addresses
        """
        self._checkDist(id)
        pass

    def distSetAlternateMailAddresses(self, id, addresses):
        """
        Sets a list of alternate mail addresses for the supplied distribution
        list. This replaces all existing alternate addresses for this list.

        @type id: string
        @param id: unique distribution list id

        @type addresses: list
        @param addresses: list of addresses

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        for address in addresses:
            self._checkMail(address)
        pass

    def distAddAlternateMailAddress(self, id, address):
        """
        Add a single mail address to the list of alternate mail addresses for
        the supplied distribution list.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        self._checkMail(address)
        pass

    def distDelAlternateMailAddress(self, id, address):
        """
        Remove a single mail address from the list of alternate mail addresses
        for the supplied distribution list.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        self._checkMail(address)
        pass

    def distGetMembers(self, id):
        """
        Read the list of member mail addresses for the supplied distribution
        list id into a list.

        @type id: string
        @param id: unique distribution list id

        @rtype: list
        @return: list of mail addresses
        """
        self._checkDist(id)
        pass

    def distAddMember(self, id, address):
        """
        Add a single mail address to the members of the supplied distribution
        list.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkMail(address)
        self._checkDist(id)
        pass

    def distDelMember(self, id, address):
        """
        Remove a single mail address from the members of the supplied
        distribution list.

        @type id: string
        @param id: unique distribution list id

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        self._checkMail(address)
        pass

    def distGetMailLimit(self, id):
        """
        Get the per mail limit for the supplied distribution list id.

        @type id: string
        @param id: unique distribution list id

        @rtype: dict
        @return: size limit in KB for incoming mails sent to this list with the
            following key: ["receive"]
        """
        self._checkDist(id)
        pass

    def distSetMailLimit(self, id, receive=None):
        """
        Set the per mail limit for the supplied distribution list id.

        @type id: string
        @param id: unique distribution list id

        @type receive: int
        @param receive: size limit in KB for incoming mails

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkDist(id)
        pass

    def folderList(self, id=None):
        """
        Get a list of all known folders from the groupware subsystem.
        Subfolders are listed as a folder, too. They are addressed
        by the complete dot separated path, while the first element indicates
        if this is a shared or a user folder.

        Example folder IDs:

        shared/folder/subfolder/subsubfolder
        user/username/folder/subfolder/subsubfolder

        @type id: string
        @param id: optional path where a listing starts

        @rtype: list
        @return: list of all folder id's
        """
        pass

    def folderAdd(self, id):
        """
        Add the specified folder to the groupware subsystem.

        @type id: string
        @param id: unique folder id

        @type location: string4321
        @param location: where to create the folder

        @type rdn: string
        @param rdn: optional location for LDAP like storage

        @rtype: bool
        @return: True on succes, False on failure
        """
        # Ensure that the base is present
        base = "/".join(id.split("/")[:-1])

        if not self.folderExists(base):
            raise GroupwareValueError(N_("Base path for folder '%s' does not exist"), id)

        # Ensure that it does not exist already
        if self.folderExists(id):
            raise GroupwareValueError(N_("Folder '%s' already exists"), id)

        # Check name
        name = id.split("/")[-1]
        if not re.match(r"^[a-z0-9 _+-]+$", name, re.IGNORECASE):
            raise GroupwareValueError(N_("Folder name '%s' contains invalid characters"), name)
        pass

    def folderDel(self, id):
        """
        Delete the specified folder from the groupware subsystem.

        @type id: string
        @param id: unique folder id

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkFolder(id)
        pass

    def folderGetMembers(self, id):
        """
        Read  groupware shard folder members into a dictionary structure.

        @type id: string
        @param id: unique folder id

        @rtype: dict
        @return: dict with the members account id as key and the permission
            as values
        """
        self._checkFolder(id)
        pass

    def folderListWithMembers(self, id):
        """
        TODO: This function could be obsolete, please check and delete it if so.
        """
        self._checkAccount()
        pass

    def folderSetMembers(self, id, members):
        """
        Write complete membership information which is defined in a
        dictionary to the groupware subsystem. This replaces all
        existing members for this folder.

        @type id: string
        @param id: unique folder id

        @type members: dict
        @param members: dict with the members account id as key and the
            permission as values

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkFolder(id)
        pass

    def folderAddMember(self, id, account_id, permission):
        """
        Add a single mail address to the members of the supplied folder.

        @type id: string
        @param id: unique folder id

        @type account_id: string
        @param account_id: account id for shared folder view

        @type permission: int
        @param permission: and'ed values of LOOKUP, READ, STATUS, WRITE,
            INSERT, POST, CREATE, DELETE, ADMINISTRATE, RIGHT_NONE, RIGHT_READ,
            RIGHT_POST, RIGHT_APPEND, RIGHT_WRITE, RIGHT_ALL

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkFolder(id)
        pass

    def folderDelMember(self, id, account_id):
        """
        Remove a single mail address from the members of the supplied
        folder.

        @type id: string
        @param id: unique folder id

        @type account_id: string
        @param account_id: account's id

        @rtype: bool
        @return: True on succes, False on failure
        """
        self._checkFolder(id)
        pass

    def folderExists(self, id):
        """
        Check if the folder exists somewhere.

        @type id: string
        @param id: folder id

        @rtype: bool
        @return: True if exists, else False
        """
        pass

    def mailAddressExists(self, address):
        """
        Check if the mail address is free for use.

        @type address: string
        @param address: mail address

        @rtype: bool
        @return: True if used, else False
        """
        self._checkMail(address)
        pass

    def getLocalDomains(self):
        """
        Return a list of local domains.

        @rtype: list
        @return: list of domains
        """
        pass
        
    def getFilterFeatures(self):
        """
        Return list of possible filter features.
        
        @rtype: list
        @return: list of possible filter features
        """
        return []

    def _checkMail(self, address):
        """
        Sanity check: bail out if there's an error in the mail address
        """
        if not isMailAddress(address):
            raise GroupwareValueError(N_("Invalid mail address: %s"), address)

    def _checkAccount(self, id):
        # Check id
        if not re.match(r"^[a-z0-9 _+-]+$", id, re.IGNORECASE):
            raise GroupwareNoSuchObject(N_("Invalid account id '%s'"), id)
        # Bail out if account does not exists
        if not self.acctExists(id):
            raise GroupwareNoSuchObject(N_("Account '%s' does not exist"), id)

    def _checkDist(self, id):
        # Bail out if distribution list does exists
        if not self.distExists(id):
            raise GroupwareNoSuchObject(N_("Distribution list '%s' does not exist"), id)

    def _checkFolder(self, id):
        # Bail out if folder does notexists
        if not self.folderExists(id):
            raise GroupwareValueError(N_("Folder '%s' does not exist"), id)
