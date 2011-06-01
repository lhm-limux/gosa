# -*- coding: utf-8 -*-
import re
import MySQLdb
from amires.resolver import PhoneNumberResolver


class SugarNumberResolver(PhoneNumberResolver):

    priority = 5

    def __init__(self):
        super(SugarNumberResolver, self).__init__()

        host = self.env.config.getOption("host", "resolver-sugar",
             default="localhost")
        user = self.env.config.getOption("user", "resolver-sugar",
            default="root")
        passwd = self.env.config.getOption("pass", "resolver-sugar",
            default="")
        base = self.env.config.getOption("base", "resolver-sugar",
            default="sugarcrm")

        # connect to sugar db
        self.sugar_db = MySQLdb.connect(host=host,
            user=user, passwd=passwd, db=base)

        self.sugar_url = self.env.config.getOption("site_url", "resolver-sugar",
            default="http://localhost/sugarcrm")

    def __del__(self):
        if hasattr(self, 'sugar_db') and self.sugar_db is not None:
            self.sugar_db.close()

    def resolve(self, number):
        number = self.replaceNumber(number)

        # split optional country code from rest of number
        res = re.match(r"^(\+([0-9]{2}))?([0-9]*)$", number)
        if res is None:
            raise NameError("'number' is not in international format")

        country = res.group(2)
        rest = res.group(3)

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
                result['company_id'] = dat[0]
                result['company_name'] = dat[1]
                result['company_phone'] = dat[2]
                result['company_detail_url'] = self.sugar_url \
                    + 'index.php?module=Accounts&action=DetailView' \
                    + '&record=' + dat[0]

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
                    result['contact_name'] = dat[1] + " " + dat[2]
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
                            result['company_id'] = dat[0]
                            result['company_name'] = dat[1]
                            result['company_phone'] = dat[2]
                            result['company_detail_url'] = self.sugar_url \
                                + 'index.php?module=Accounts&action=DetailView'\
                                + '&record=' + dat[0]
        finally:
            # clean up
            cursor.close()

        # return what was found
        if found == False:
            return None

        result['resource'] = 'sugar'
        return result
