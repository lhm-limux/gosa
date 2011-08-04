# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 609 2010-08-16 08:19:05Z cajus $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
import urllib
import hashlib

from gosa.common.components.command import Command
from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_
from gosa.common import Environment

class GravatarUtils(Plugin):
    """
    Utility class that contains methods needed to retrieve gravatar
    URLs.
    """
    _target_ = 'gravatar'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

    @Command(__doc__=N_("Generate samba lm:nt hash combination "+
        "from the supplied password."))
    def getGravatarURL(self, mail, size=40, url="http://www.gonicus.de"):
        gravatar_url = "http://www.gravatar.com/avatar.php?"
        gravatar_url += urllib.urlencode({
            'gravatar_id': hashlib.md5(mail.lower()).hexdigest(),
            'default': url,
            'size': str(size)})
        return gravatar_url
