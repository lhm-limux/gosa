# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: __init__.py 858 2010-09-07 05:56:59Z cajus $$

 See LICENSE for more information about the licensing.
"""
__version__ = __import__('pkg_resources').get_distribution('gosa.dbus').version
__import__('pkg_resources').declare_namespace(__name__)
