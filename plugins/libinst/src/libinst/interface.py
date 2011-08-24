# -*- coding: utf-8 -*-
"""
Repository modules are used to deliver a unique API for managing
various repositories. This can be a Debian repository, RPM repository
or i.e. a set of OPSI products.

Modules get registered thru the setuptools ``[libinst.repository]`` section
and are available automatically.
"""
from inspect import stack


class DistributionHandler(object):
    """
    This is the interface class for handling repositories.
    """

    #TODO: this is not complete, inherritants have grown away

    def createDistribution(self, session, name, mirror=None):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def removeDistribution(self, session, name):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def createRelease(self, session, distribution, name, parent=None):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def removeRelease(self, session, name):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def renameRelease(self, session, source_name, target_name):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def addPackage(self, session, url, release=None):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def _updateInventory(self, session, distribution=None, release=None):
        """
        TODO
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])
