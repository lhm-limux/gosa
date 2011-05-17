# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: utils.py 1208 2010-10-21 11:40:16Z cajus $$

 This is part of the samba module and provides some utilities.

 See LICENSE for more information about the licensing.
"""
from unidecode import unidecode
from gosa.common.components.command import Command
from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_


class MiscUtils(Plugin):
    _target_ = 'misc'

    @Command(__doc__=N_("Transliterate a given string"))
    def transliterate(self, string):
        table = {
            ord(u'ä'): u'ae',
            ord(u'ö'): u'oe',
            ord(u'ü'): u'ue',
            ord(u'Ä'): u'Ae',
            ord(u'Ö'): u'Oe',
            ord(u'Ü'): u'Ue',
            }
        string = string.translate(table)
        return unidecode(string)
