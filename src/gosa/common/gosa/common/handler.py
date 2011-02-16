# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: handler.py 608 2010-08-16 08:12:35Z cajus $$

 See LICENSE for more information about the licensing.
"""
import zope.interface


class IInterfaceHandler(zope.interface.Interface):
    """ Mark a plugin to be the manager for a special interface """
    pass


class IPluginHandler(zope.interface.Interface):
    """ Mark a plugin to be the manager for a special interface """
    pass
