# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: manager.py 1356 2010-11-15 09:09:29Z cajus $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
from inspect import stack
from base import Groupware
from gosa.agent.command import Command
from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_
from gosa.common.env import Environment
import pkg_resources
import gettext

# Initialize localisation
t = gettext.translation('messages', pkg_resources.resource_filename("libgroupware", "locale"), fallback=True)
_ = t.ugettext


class GroupwareManager(Groupware, Plugin):
    """
    This is the groupware command proxy. It is the abstraction layer between
    the original backend and the client.
    """

    _target_ = 'groupware'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

        # Register available handlers
        self.type_reg= {}
        for entry in pkg_resources.iter_entry_points("libgroupware.implementations"):
            module = entry.load()
            self.env.log.info("groupware handler %s included" % module.__name__)
            self.type_reg[module.getName()] = module()

        # Read configuration
        self.__backend_name = env.config.getOption('backend', section = 'groupware')
        if not self.__backend_name:
            raise ValueError(N_("No groupware backend specified in configuration [groupware] section"))
        if not self.__backend_name in self.type_reg:
            raise ValueError(N_("Groupware backend '%s' is not supported"), self.__backend_name)

        self.__backend = self.type_reg[self.__backend_name]

        # Create a mapping for all the following functions, marking
        # them as a @Command and provide i18n __doc__ for use with
        # the shell
        for name, doc in {
            'gwGetCapabilities': N_("Return a capability descriptor to determine the functionality of a handler"),
            'gwGetMailboxLocations': N_("Get a list of all available mailbox locations"),
            'gwAcctList': N_("Get a list of all known groupware accounts"),
            'gwAcctExists': N_("Check if the given groupware account exists"),
            'gwAcctAdd': N_("Add the specified account including the initial mail address to the groupware subsystem"),
            'gwAcctSetLocation': N_("Set the accounts mailbox location. May migrate the account to another location (same backend)"),
            'gwAcctGetLocation': N_("Retrieve the accounts mailbox location"),
            'gwAcctSetEnabled': N_("Enable or disable account"),
            'gwAcctGetStatus': N_("Retrieve the account status"),
            'gwAcctDel': N_("Delete the specified account id from the groupware subsystem"),
            'gwAcctGetProperties': N_("Get account property flags, indicating what services the account is allowed to use"),
            'gwAcctGetSupportedProperties': N_("Return dictionary of supported properties that can be set for the specified account"),
            'gwAcctSetProperties': N_("Set account property flags, indicating what services the account is allowed to use"),
            'gwAcctGetPrimaryMailAddress': N_("Read the primary mail address of the supplied account id"),
            'gwAcctSetPrimaryMailAddress': N_("Set the primary mail address for the supplied account id"),
            'gwAcctGetAlternateMailAddresses': N_("Read the list of alternate mail addresses for the supplied account into a list"),
            'gwAcctSetAlternateMailAddresses': N_("Sets a list of alternate mail addresses for the supplied account. This replaces all existing alternate addresses for this account"),
            'gwAcctAddAlternateMailAddress': N_("Add a single mail address to the list of alternate mail addresses for the supplied account"),
            'gwAcctDelAlternateMailAddress': N_("Remove a single mail address from the list of alternate mail addresses for the supplied account"),
            'gwAcctGetMailForwardAddresses': N_("Read the list of forward mail addresses for the supplied account"),
            'gwAcctSetMailForwardAddresses': N_("Sets a dictionary of forward mail addresses / redirect flag entries"),
            'gwAcctAddMailForwardAddress': N_("Add a single mail address / redirect flag to the list of forward addresses for the supplied account"),
            'gwAcctDelMailForwardAddress': N_("Remove a single mail address from the list of forward mail addresses for the supplied account"),
            'gwAcctGetOutOfOfficeReply': N_("Returns a dictionary for the out of office reply mechanism"),
            'gwAcctSetOutOfOfficeReply': N_("Set or disable the out of office reply message"),
            'gwAcctGetQuota': N_("Returns a dictionary containing quota information for the specified account id"),
            'gwAcctSetQuota': N_("Specify the quota settings for the supplied account"),
            'gwAcctGetMailLimit': N_("Get the per mail limit for the supplied account id"),
            'gwAcctSetMailLimit': N_("Set the per mail limit for the supplied account id"),
            'gwAcctGetFilters': N_("Get the list of defined filters for the supplied account id"),
            'gwAcctSetFilters': N_("Set a list of filters for the supplied account id"),
            'gwAcctDelFilter': N_("Remove a single filter from the supplied account id"),
            'gwDistList': N_("Get a list of all known groupware distribution lists"),
            'gwDistExists': N_("Check if the distribution list exists somewhere"),
            'gwDistAdd': N_("Add the specified distribution list including the initial mail address to the groupware subsystem"),
            'gwDistDel': N_("Delete the specified distribution list from the groupware subsystem"),
            'gwDistRename': N_("Rename the specified distribution list from the groupware subsystem"),
            'gwDistGetPrimaryMailAddress': N_("Read the primary mail address of the supplied distribution list id"),
            'gwDistSetPrimaryMailAddress': N_("Set the primary mail address for the supplied distribution list id"),
            'gwDistGetAlternateMailAddresses': N_("Read the list of alternate mail addresses for the supplied distribution list into a list"),
            'gwDistSetAlternateMailAddresses': N_("Sets a list of alternate mail addresses for the supplied distribution list"),
            'gwDistAddAlternateMailAddress': N_("Add a single mail address to the list of alternate mail addresses for the supplied distribution list"),
            'gwDistDelAlternateMailAddress': N_("Remove a single mail address from the list of alternate mail addresses for the supplied distribution list"),
            'gwDistGetMembers': N_("Read the list of member mail addresses for the supplied distribution list id into a list"),
            'gwDistAddMember': N_("Add a single mail address to the members of the supplied distribution list"),
            'gwDistDelMember': N_("Remove a single mail address from the members of the supplied distribution list"),
            'gwDistGetMailLimit': N_("Get the per mail limit for the supplied distribution list id"),
            'gwDistSetMailLimit': N_("Set the per mail limit for the supplied distribution list id"),
            'gwFolderList': N_("Get a list of all known folders from the groupware subsystem"),
            'gwFolderAdd': N_("Add the specified folder to the groupware subsystem"),
            'gwFolderDel': N_("Delete the specified folder from the groupware subsystem"),
            'gwFolderGetMembers': N_("Read  groupware shard folder members into a dictionary structure"),
            'gwFolderSetMembers': N_("Write complete membership information"),
            'gwFolderAddMember': N_("Add a single mail address to the members of the supplied folder"),
            'gwFolderDelMember': N_("Remove a single mail address from the members of the supplied folder."),
            'gwFolderExists': N_("Check if the folder exists somewhere"),
            'gwMailAddressExists': N_("Check if the mail address is free for use"),
            'gwGetLocalDomains': N_("Return a list of local domains"),
            'gwGetFilterFeatures': N_("Return list of possible filter features"),
            'gwFolderListWithMembers': N_("Return list of folder with corresponding ACLs"),
            'gwAcctGetComprehensiveUser': N_("Return comprehensive data from the given account - for speedup")
            }.iteritems():

            def mixedCase(word):
                """ Make the first character lowercase """
                return word[0].lower() + word[1:]

            def mthd_wrap(dst):
                """ Wrap function to avoid name references """

                def mthd(self, *args):
                    return getattr(self.__backend, mixedCase(dst[2:]))(*args)

                # Install class method as 'dst', adding the
                # command flag and __doc__
                mthd.__doc__ = doc
                mthd.isCommand = True
                setattr(self.__class__, dst, mthd)

            # Install wrapped method
            mthd_wrap(name)

    @Command(__doc__=N_("Verify list of uids"))
    def gwVerifyAcct(self, uid_list):
        accounts = self.gwAcctList()
        uids = dict(map(lambda x:(x,None), uid_list))
        for uid in [u for u in uid_list if u in accounts]:
            uids[uid] = accounts[uid]
        return uids

    @Command(__doc__=N_("Get list of available groupware handlers"))
    def gwGetHandlers(self):
        return self.type_reg.keys()
