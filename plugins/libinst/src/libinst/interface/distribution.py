# -*- coding: utf-8 -*-
"""
Distribution modules are used to deliver a unique API for managing
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
        Create a new distribution with a specific name.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        name            The name of the new distribution (i.e. debian)
        mirror          Specifies an optional mirror origin, distribution will be unmanaged
        =============== ==================================
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def removeDistribution(self, session, name, recursive=False):
        """
        Removes specified distribution (must not have any releases), removal of releases has to be forced.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        name            The name of the distribution to be removed.
        recursive       Choose whether to force removal of all releases depending on this distribution.
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def createRelease(self, session, distribution, name):
        """
        Creates a new release in the given distribution.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        distribution    The name of the distribution this release belongs to.
        name            The name for the new release, parent releases are prepended with slashes (i.e. "lenny/production")
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def removeRelease(self, session, release, recursive=False):
        """
        Removes specified release (removal of child releases needs to be forced).
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        release         The name of the release to remove.
        recursive       Choose whether method should remove child releases.
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def renameRelease(self, session, source, target):
        """
        Renames specified release.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        source          The name of the release that should be renamed.
        target          The new name for the release

        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def addPackage(self, session, url, distribution=None, release=None):
        """
        Adds a local or remote specified package to the given distribution or release.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        url             URL of package, can be a local or remote path (supported are ftp/http/https URLs).
        distribution    The name of the distribution to which this package should be added (adds the package to all releases of the distribution)
        release         The name of the release to which this package should be added.
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def _updateInventory(self, session, release=None, distribution=None):
        """
        Updates package indexes for the given release or distribution.
        =============== ==================================
        Parameter       Description
        =============== ==================================
        session         The sqlalchemy session to use.
        release         Update package index for specific release (including child releases).
        distribution    The name of the distribution which should be updated (all releases including child releases).
