# -*- coding: utf-8 -*-
import time
from lxml import etree
from amires.resolver import PhoneNumberResolver


class XMLNumberResolver (PhoneNumberResolver):

    priority = 2
    ttl = -1# no need to cache from cache

    def __init__(self):
        super(XMLNumberResolver, self).__init__()

        # read config
        filename = self.env.config.getOption("filename", "resolver-xml",
             default="./numbers.xml")

        try:
            self.priority = float(self.env.config.getOption("priority",
                "resolver-xml", default=str(self.priority)))
        except:
            # leave default priority
            pass

        xml = etree.parse(filename).getroot()

        self.numbers = {}
        for entry in xml:
            number = entry.get("number")
            self.numbers[number] = {
                'company_id': '',
                'company_name': '',
                'company_phone': '',
                'company_detail_url': '',
                'contact_id': '',
                'contact_name': '',
                'contact_phone': number,
                'ldap_uid': '',
                'contact_detail_url': '',
                'ttl': self.ttl,
                'timestamp': time.time()}
            for e in entry:
                if e.tag not in self.numbers[number]:
                    raise RuntimeError("Invalid XML element while parsing.")

                self.numbers[number][e.tag] = e.text

    def resolve(self, number):
        if number in self.numbers:
            self.numbers[number]['resource'] = "xml"
            return self.numbers[number]
        else:
            return None
