# -*- coding: utf-8 -*-
from unidecode import unidecode
from gosa.common.components import Command
from gosa.common.components import Plugin
from gosa.common.utils import N_


class MiscUtils(Plugin):
    _target_ = 'misc'

    @Command(__help__=N_("Transliterate a given string"))
    def transliterate(self, string):
        """
        Deliver a plain ASCII value of the given string by
        additionaly replacing a couple of known characters
        by their ASCII versions.

        ========= =========================
        Parameter Description
        ========= =========================
        string    String to be ASCIIfied
        ========= =========================

        ``Return:`` ASCII string
        """
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
