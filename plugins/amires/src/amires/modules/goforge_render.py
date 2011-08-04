# -*- coding: utf-8 -*-
import cgi
import MySQLdb
import pkg_resources
import gettext
from amires.render import BaseRenderer
from gosa.common.env import Environment

# Set locale domain
t = gettext.translation('messages', pkg_resources.resource_filename("amires", "locale"), fallback=False)
_ = t.ugettext


class GOForgeRenderer(BaseRenderer):

    priority = 10

    def __init__(self):
        self.env = env = Environment.getInstance()
        host = env.config.get("fetcher-goforge.host",
            default="localhost")
        user = env.config.get("fetcher-goforge.user",
            default="root")
        passwd = env.config.get("fetcher-goforge.pass",
            default="")
        db = env.config.get("fetcher-goforge.base",
            default="goforge")

        # connect to GOforge db
        self.forge_db = MySQLdb.connect(host=host,
            user=user, passwd=passwd, db=db)

        self.forge_url = self.env.config.get("fetcher-goforge.site_url",
            default="http://localhost/")

    def getHTML(self, particiantInfo, event):
        super(GOForgeRenderer, self).getHTML(particiantInfo)

        if not 'company_id' in particiantInfo:
            return ""

        company_id = particiantInfo['company_id']
        if not company_id:
            return ""

        # prepare result
        result = []

        cursor = self.forge_db.cursor()

        try:
            # obtain GOforge internal customer id
            leng = cursor.execute("""
                SELECT customer_id
                FROM customer
                WHERE customer_unique_ldap_attribute = %s""",
                (company_id,))
            row = cursor.fetchone()

            # if entry for company exists ...
            if leng == 1:
                # fetch tickets from database
                leng = cursor.execute("""
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
                        'group_id': row[2],
                        'assigned': row[3]})

        finally:
            cursor.close()

        if len(result) == 0:
            return ""

        html = "<b>%s</b>" % _("Open GOForge tickets")
        for row in result:
            html += "\n<a href='%s'>%s</a>: '%s'" %(
                cgi.escape(self.forge_url + "/bugs/?func=detailbug" \
                    + "&bug_id=" + str(row['id']) \
                    + "&group_id=" + str(row['group_id'])),
                row['id'],
                row['summary'].encode("ascii", "xmlcharrefreplace"))

        return html
