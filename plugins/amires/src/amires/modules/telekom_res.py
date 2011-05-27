# -*- coding: utf-8 -*-
import re
import sys
import urllib
import urllib2
from urlparse import urlparse, parse_qs
from amires.resolver import PhoneNumberResolver


class TelekomNumberResolver(PhoneNumberResolver):
    priority = 99

    def __init__(self):
        super(TelekomNumberResolver, self).__init__()

        #TODO: internal
        self.internal = 3

    def build_string(self, src, *keys):
        """
        Assemble a string from a dict using optional keys.
        """
        return unicode(
            " ".join(map(lambda x: src[x][0],
                filter(lambda k: k in src, keys))),
            'latin1').encode('utf-8')

    def resolve(self, number):
        """
        Probe a couple of numbers in order to find one which is
        available in the official phone book. Number needs to be
        normalized to internatial format (+...) with nothing but
        the starting + and digits.
        """
        number = self.replaceNumber(number)

        if not re.match(r"\+\d{4,}", number):
            raise ValueError("number needs to be in stripped international format")

        # Does the number match completely?
        res = self._resolve_telekom(number)
        if res:
            return res

        # Try to find extensions padded with a '0' which may be used
        # as a "hotline" number
        for ext in range(self.internal, 1, -1):
            res = self._resolve_telekom(number[0:-ext] + '0')
            if res:
                return res

        # Nothing found
        return None

    def _resolve_telekom(self, number):
        """
        This is a hack to resolve a number via "www.dastelefonbuch.de" powered
        by the Deutsche Telekom. It will break if they change some links inside
        their result website, actually.
        """

        # URL and fixed POST elements
        url = 'http://www1.dastelefonbuch.de/'
        values = {'kw': number, "cifav": "0", "s": "a20000", "la": "de",
            "taoid": "", "cmd": "search", "ort_ok": "0", "sp": "3",
            "vert_ok": "0", "aktion": "23"}

        # POST request and prepare response
        data = urllib.urlencode(values)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)

        loc = re.compile(r'.*href="([^"]+)".*')
        lin = re.compile(r'.*[^_]nachname=.*')

        # Parse lines until we find a href with a 'nachname' definition
        for line in filter(lin.match, response.readlines()):

            url_g = loc.match(line.strip())
            if not url_g:
                return None

            # First match wins, extract data - pylint: disable-msg=E1101
            out = parse_qs(urlparse(urllib.unquote(url_g.groups()[0])).query)

            return {
                'name': self.build_string(out, 'vorname', 'nachname'),
                'street': self.build_string(out, 'strasse', 'hausnummer'),
                'location': self.build_string(out, 'plz', 'ort'),
                'number': number
            }

        # Nothing found
        return None
