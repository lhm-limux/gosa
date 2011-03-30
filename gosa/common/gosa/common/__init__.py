# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: __init__.py 610 2010-08-16 08:39:53Z cajus $$

 See LICENSE for more information about the licensing.
"""

__version__ = __import__('pkg_resources').get_distribution('gosa.common').version
__import__('pkg_resources').declare_namespace(__name__)
