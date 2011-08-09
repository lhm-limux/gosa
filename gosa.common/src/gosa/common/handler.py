# -*- coding: utf-8 -*-
"""
The usage of the zope interface is in progress. Currently, it is just used as a
marker.
"""
import zope.interface


class IInterfaceHandler(zope.interface.Interface):
    """ Mark a plugin to be the manager for a special interface """
    pass


class IPluginHandler(zope.interface.Interface):
    """ Mark a plugin to be the manager for a special interface """
    pass
