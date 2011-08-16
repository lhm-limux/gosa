# -*- coding: utf-8 -*-


class DistributionHandler(object):
    def createDistribution(self, session, name, mirror=None):
        pass

    def removeDistribution(self, session, name):
        pass

    def createRelease(self, session, distribution, name, parent=None):
        pass

    def removeRelease(self, session, name):
        pass

    def renameRelease(self, session, source_name, target_name):
        pass

    def addPackage(self, session, url, release=None):
        pass

    def _updateInventory(self, session, distribution=None, release=None):
        pass
