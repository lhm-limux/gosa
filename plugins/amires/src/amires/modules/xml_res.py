# -*- coding: utf-8 -*-
from lxml import etree
from amires.resolver import PhoneNumberResolver


class XMLNumberResolver (PhoneNumberResolver):

    priority = 2

    def __init__(self):
        super(XMLNumberResolver, self).__init__()

        filename = self.env.config.getOption("filename", "resolver-xml",
             default="./numbers.xml")
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
                'contact_detail_url': ''}
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
