# -*- coding: utf-8 -*-
import time
import cgi
import pkg_resources
import gettext
from amires.render import BaseRenderer
from gosa.common.env import Environment

# Set locale domain
t = gettext.translation('messages', pkg_resources.resource_filename("amires",
"locale"),
        fallback=False)
_ = t.ugettext


class CacheInfoRenderer(BaseRenderer):

    priority = 1

    def __init__(self):
        pass

    def getHTML(self, info, event):
        super(CacheInfoRenderer, self).getHTML(info)

        # is resource cached?
        if info['resource'] != "CacheNumberResolver":
            return ""

        # compute days, hours, minutes and seconds
        d = int(time.time() - info['timestamp'])
        d,s = divmod(d,60)
        d,m = divmod(d,60)
        d,h = divmod(d,24)

        # assemble time string
        txt = _("%d seconds") % s
        if m > 0:
            txt = _("%d minutes and %s") %(m, txt)
            if h > 0:
                txt = _("%d hours, %s") %(h, txt)
                if d > 0:
                    txt = _("%d days, %s") %(d, txt)

        # assemble html string
        html = "<b>" + _("This is a cached info") + "</b>\n"
        html += _("Added to cache %s ago.") % txt

        return html

