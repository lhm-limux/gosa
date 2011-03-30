# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: manager.py 1307 2010-10-27 07:59:13Z cajus $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
import gettext
from gosa.common.components.registry import PluginRegistry
from gosa.common.utils import N_
from gosa.common.env import Environment
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages',
    resource_filename("libgroupware.exchange", "locale"),
    fallback=True)
_ = t.ugettext


class ExchangeManager(object):

    def __init__(self, name=None, cs=None, client=None):
        self.__name = name
        self.__client = client

        if not cs:
            env = Environment.getInstance()
            self.__client = env.config.getOption("exchange_client",
                    "groupware", None)
            if not self.__client:
                raise ValueError(N_("Exchange plugin is unconfigured. Please set a value for 'exchange_client' in the 'groupware' section of your configuration."))

            self.__cs = PluginRegistry.getInstance('ClientService')
        else:
            self.__cs = cs

    def __getattr__(self, name):
        if self.__name != None:
            name = "%s.%s" % (self.__name, name)

        return ExchangeManager(name, self.__cs, self.__client)

    def __call__(self, *args):
        return self.__cs.clientDispatch(self.__client, self.__name, *args)

    @staticmethod
    def getName():
        return "Exchange"


