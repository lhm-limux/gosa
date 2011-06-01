# -*- coding: utf-8 -*-
import MySQLdb
from gosa.common.env import Environment


class BubbleSectionBuilder(object):
    def __init__(self):
        pass

    def getHTML(self, particiantInfo):
        if not particiantInfo:
            raise RuntimeError("particiantInfo must not be None.")
        if type(particiantInfo) is not dict:
            raise TypeError("particiant Info must be a dictionary.")


class MainSection(BubbleSectionBuilder):
    def __init__(self):
        pass

    def getHTML(self, particiantInfo):
        super(MainSection, self).getHTML(particiantInfo)

        p = particiantInfo

        # build html for company name
        comp = ""
        if p['company_name'] != "":
            if p['company_detail_url']:
                comp += "<a href='%s'>%s</a>" %(
                    p['company_detail_url'],
                    p['company_name'])
            else:
                comp += p['company_name']

        # build html for contact name
        cont = ""
        if p['contact_name'] != "":
            if p['contact_detail_url'] != "":
                cont += "<a href='%s'>%s</a>" %(
                    p['contact_detail_url'],
                    p['contact_name'])
            else:
                cont += p['contact_name']

        # build actual html section
        html = ""
        if cont != "":
            html += cont
            if comp != "":
                html += " (" + comp + ")"

        return html


class GOforgeSection(BubbleSectionBuilder):

    def __init__(self):
        self.env = env = Environment.getInstance()
        host = env.config.getOption("host", "fetcher-goforge",
            default="localhost")
        user = env.config.getOption("user", "fetcher-goforge",
            default="root")
        passwd = env.config.getOption("pass", "fetcher-goforge",
            default="")
        db = env.config.getOption("base", "fetcher-goforge",
            default="goforge")

        # connect to GOforge db
        self.forge_db = MySQLdb.connect(host=host,
            user=user, passwd=passwd, db=db)

    def getHTML(self, particiantInfo):
        super(GOforgeSection, self).getHTML(particiantInfo)

        company_id = particiantInfo['company_id']
        if company_id == "":
            return ""

        # prepare result
        result = []

        cursor = self.forge_db.cursor()

        try:
            # obtain GOforge internal customer id
            len = cursor.execute("""
                SELECT customer_id
                FROM customer
                WHERE customer_unique_ldap_attribute = %s""",
                (company_id,))
            row = cursor.fetchone()

            # if entry for company exists ...
            if len == 1:
                # fetch tickets from database
                len = cursor.execute("""
                    SELECT bug.bug_id, bug.summary,
                        bug.group_id, user.user_name
                    FROM bug, user
                    WHERE bug.status_id = 1
                        AND bug.assigned_to = user.user_id
                        AND bug.customer_id = %s
                    LIMIT 29;""",
                    (row[0],))

                rows = cursor.fetchall()

                # put results into dictionary
                for row in rows:
                    result.append({'id': row[0],
                        'summary': row[1],
                        'priority': row[2],
                        'assigned': row[3]})

        finally:
            cursor.close()

        html = "<h2>GOforge</h2><ul>"
        for row in result:
            html += "<li>%s: '%s'</li>" %(row['id'], row['summary'])
        html += "</ul>"

        return html

