# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: manage.py 486 2010-08-10 07:21:33Z cajus $$

 See LICENSE for more information about the licensing.
"""

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
