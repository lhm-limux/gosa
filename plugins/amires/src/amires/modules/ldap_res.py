# -*- coding: utf-8 -*-
import ldap
from gosa.agent.ldap_utils import LDAPHandler
from amires.resolver import PhoneNumberResolver
from gosa.common.components.cache import cache


class LDAPNumberResolver(PhoneNumberResolver):

    priority = 4

    def __init__(self):
        super(LDAPNumberResolver, self).__init__()

        try:
            self.priority = float(self.env.config.get("resolver-ldap.priority",
                default=str(self.priority)))
        except:
            # leave default priority
            pass

    @cache(ttl=3600)
    def resolve(self, number):
        number = self.replaceNumber(number)

        filtr = ldap.filter.filter_format("(&(uid=*)(telephoneNumber=%s))", str(number))
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
                        'contact_name': unicode(res[0][1]['cn'][0], 'UTF-8'),
                        'contact_phone': res[0][1]['telephoneNumber'][0],
                        'contact_detail_url': '',
                        'ldap_uid': res[0][1]['uid'][0],
                        'resource': 'ldap',
                }
                return result
            else:
                return None
