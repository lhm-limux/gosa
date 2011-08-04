# -*- coding: utf-8 -*-
import re
import MySQLdb
from amires.resolver import PhoneNumberResolver
from gosa.common.components.cache import cache


class SugarNumberResolver(PhoneNumberResolver):

    priority = 5

    def __init__(self):
        super(SugarNumberResolver, self).__init__()

        host = self.env.config.get("resolver-sugar.host",
             default="localhost")
        user = self.env.config.get("resolver-sugar.user",
            default="root")
        passwd = self.env.config.get("resolver-sugar.pass",
            default="")
        base = self.env.config.get("resolver-sugar.base",
            default="sugarcrm")

        try:
            self.priority = float(self.env.config.get("resolver-sugar.priority",
                default=str(self.priority)))
        except:
            # leave default priority
            pass

        # connect to sugar db
        self.sugar_db = MySQLdb.connect(host=host,
            user=user, passwd=passwd, db=base)
        self.sugar_db.set_character_set('utf8')

        self.sugar_url = self.env.config.get("resolver-sugar.site_url",
            default="http://localhost/sugarcrm")

    def __del__(self):
        if hasattr(self, 'sugar_db') and self.sugar_db is not None:
            self.sugar_db.close()

    @cache(ttl=3600)
    def resolve(self, number):
        number = self.replaceNumber(number)

        # split optional country code from rest of number
        res = re.match(r"^(\+([0-9]{2}))?([0-9]*)$", number)
        if res is None:
            raise NameError("'number' is not in international format")

        country = res.group(2)
        rest = res.group(3)

        print res.group(0)

        found = False

        # build regular expression for DB search
        sep = "[-[:blank:]/\(\)]*"
        regex = "^"

        if country is not None:
            regex += r"((\\+" + country + ")|(0))" + sep
            regex += r"\(0\)?" + sep

        for c in rest:
            regex += c + sep

        regex += "$"

        # query database
        result = {
            'company_id': '',
            'company_name': '',
            'company_phone': '',
            'company_detail_url': '',
            'contact_id': '',
            'contact_name': '',
            'contact_phone': '',
            'contact_detail_url': '',
            'ldap_uid': '',
            'resource': 'sugar'}

        cursor = self.sugar_db.cursor()

        try:
            # query for accounts
            cursor.execute("""
                SELECT id, name, phone_office
                FROM accounts
                WHERE phone_office REGEXP '%s'""" % (regex))
            dat = cursor.fetchone()

            if dat is not None:
                # fill result data with found data
                if dat[0] is not None:
                    result['company_id'] = dat[0]
                    result['company_detail_url'] = self.sugar_url \
                        + 'index.php?module=Accounts&action=DetailView' \
                        + '&record=' + dat[0]
                if dat[1] is not None:
                    result['company_name'] = unicode(dat[1], "UTF-8")
                if dat[2] is not None:
                    result['company_phone'] = dat[2]

                found = True
            else:
                # query for contacts
                cursor.execute("""SELECT id, first_name, last_name, phone_work
                    FROM contacts
                    WHERE phone_work REGEXP '%s'
                    OR phone_home REGEXP '%s'
                    OR phone_mobile REGEXP '%s'
                    OR phone_other REGEXP '%s'""" %
                    (regex, regex, regex, regex))
                dat = cursor.fetchone()

                if dat is not None:
                    # fill result data with found data
                    result['contact_id'] = dat[0]
                    if dat[1] is not None:
                        result['contact_name'] = unicode(dat[1], "UTF-8")
                    if dat[2] is not None:
                        if not result['contact_name'] == '':
                            result['contact_name'] += ' '
                        result['contact_name'] += unicode(dat[2], "UTF-8")
                    if dat[3] is not None:
                        result['contact_phone'] = dat[3]
                    result['contact_detail_url'] = self.sugar_url \
                        + 'index.php?module=Contacts&action=DetailView' \
                        + '&record=' + dat[0]

                    found = True

                    cursor.execute("""SELECT account_id
                        FROM accounts_contacts
                        WHERE contact_id = %s """,
                        (dat[0],))
                    dat = cursor.fetchone()

                    if dat is not None:
                        cursor.execute("""SELECT id, name, phone_office
                            FROM accounts
                            WHERE id = %s""",
                            (dat[0],))
                        dat = cursor.fetchone()

                        if dat is not None:
                            if dat[0] is not None:
                                result['company_id'] = dat[0]
                                result['company_detail_url'] = self.sugar_url \
                                    + 'index.php?module=Accounts&action=DetailView'\
                                    + '&record=' + dat[0]
                            if dat[1] is not None:
                                result['company_name'] = unicode(dat[1], "UTF-8")
                            if dat[2] is not None:
                                result['company_phone'] = dat[2]
        finally:
            # clean up
            cursor.close()

        # return what was found
        if found == False:
            return None

        result['resource'] = 'sugar'
        return result
