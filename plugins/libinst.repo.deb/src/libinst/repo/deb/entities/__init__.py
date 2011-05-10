# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: __init__.py 487 2010-08-10 07:34:06Z cajus $$

 See LICENSE for more information about the licensing.
"""
__import__('pkg_resources').declare_namespace(__name__)
# pylint: disable-msg=E0611
from pkg_resources import resource_filename
import gettext

# Include locales
t = gettext.translation('messages', resource_filename("libinst.repo.deb", "locale"), fallback=True)
_ = t.ugettext
