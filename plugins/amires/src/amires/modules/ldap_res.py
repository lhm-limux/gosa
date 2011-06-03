# -*- coding: utf-8 -*-
import ldap
import time
from gosa.agent.ldap_utils import LDAPHandler
from amires.resolver import PhoneNumberResolver


class LDAPNumberResolver(PhoneNumberResolver):

    priority = 4
    ttl = 30

    def __init__(self):
        super(LDAPNumberResolver, self).__init__()

        try:
            self.priority = float(self.env.config.getOption("priority",
                "resolver-ldap", default=str(self.priority)))
        except:
            # leave default priority
            pass

        try:
            self.ttl = float(self.env.config.getOption("ttl",
                "resolver-ldap", default=str(self.ttl)))
        except:
            pass


    def resolve(self, number):
        number = self.replaceNumber(number)

        filtr = "telephoneNumber=" + number
        attrs = ['cn', 'uid', 'telephoneNumber']

        # search ldap
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE, filtr, attrs)
            if len(res) == 1:
                result = {
                        'company_id': '',
                        'company_name': 'Intern',
                        'company_phone': '',
                        'company_detail_url': '',
                        'contact_id': res[0][1]['uid'][0],
                        'contact_name': res[0][1]['cn'][0],
                        'contact_phone': res[0][1]['telephoneNumber'][0],
                        'contact_detail_url': '',
                        'ldap_uid': res[0][1]['uid'][0],
                        'resource': 'ldap',
                        'ttl': self.ttl, # I'd also rather not cache very long, here
                        'timestamp': time.time()
                }
                return result
            else:
                return None
