# -*- coding: utf-8 -*-
import smbpasswd

from gosa.common.components import Command
from gosa.common.components import Plugin
from gosa.common.utils import N_
from gosa.common import Environment

class SambaUtils(Plugin):
    """
    Utility class that contains methods needed to handle samba
    functionality.
    """
    _target_ = 'samba'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

    @Command(__help__=N_("Generate samba lm:nt hash combination "+
        "from the supplied password."))
    def mksmbhash(self, password):
        return '%s:%s' % smbpasswd.hash(password)
