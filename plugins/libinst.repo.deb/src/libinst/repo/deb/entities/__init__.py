# -*- coding: utf-8 -*-
__import__('pkg_resources').declare_namespace(__name__)
# pylint: disable-msg=E0611
from pkg_resources import resource_filename
import gettext

# Include locales
t = gettext.translation('messages', resource_filename("libinst.repo.deb", "locale"), fallback=True)
_ = t.ugettext
