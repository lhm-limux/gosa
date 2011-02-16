# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: event.py 279 2010-06-29 15:22:34Z cajus $$

 This is the Event object. It constructs events to be sent thru the
 org.gosa.event topics.

 See LICENSE for more information about the licensing.
"""


class BaseInstallMethod(object):

    def __init__(self, data):
        self.data = data

    def getBootConfiguration(self):
        return None

    def getBootString(self):
        return None
