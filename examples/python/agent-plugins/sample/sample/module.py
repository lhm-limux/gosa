# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: manage.py 1277 2010-10-22 14:31:42Z janw $$

 See LICENSE for more information about the licensing.
"""
import gettext

from gosa.common import Environment
from gosa.common.components.command import Command
from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_
# pylint: disable-msg=E0611
from pkg_resources import resource_filename

# Setup locales
t = gettext.translation('messages', resource_filename("sample", "locale"), fallback=True)
_ = t.ugettext


class SampleModule(Plugin):
    _target_ = 'sample'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

        self.message =  self.env.config.get('sample.message',
                default=_('No message configured!'))

    @Command(__doc__=N_("Return a pre-defined message to the caller"))
    def hello(self, name="unknown"):
        return _("Hello %s!") % name

    @Command(__doc__=N_("Return a configured message to the caller"))
    def hello2(self):
        return self.message
