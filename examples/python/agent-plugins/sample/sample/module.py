# -*- coding: utf-8 -*-
import gettext

from gosa.common import Environment
from gosa.common.components import Command, Plugin
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

    @Command(__help__=N_("Return a pre-defined message to the caller"))
    def hello(self, name="unknown"):
        return _("Hello %s!") % name

    @Command(__help__=N_("Return a configured message to the caller"))
    def hello2(self):
        return self.message
