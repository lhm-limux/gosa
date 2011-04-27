# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2011 GONICUS GmbH

 See LICENSE for more information about the licensing.
"""
from libinst.methods import BaseInstallMethod


class DebianPreseed(BaseInstallMethod):

    @staticmethod
    def getInfo():
        return {
            "name": "Preseed",
            "title": "Debian preseed installation method",
            "description": "Description",
            }
