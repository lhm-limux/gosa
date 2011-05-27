# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""
import gettext
import os
import select
import subprocess

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.distribution import Distribution

from gosa.common.env import Environment
from gosa.common.utils import N_, locate

# pylint: disable-msg=E0611
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("libinst.repo.deb", "locale"), fallback=True)
_ = t.ugettext

class DebianDistribution(Distribution, UseInnoDB):
    __tablename__ = 'debian_distribution'
    __mapper_args__ = {'polymorphic_identity': 'debian_distribution'}
    id = Column(Integer,
                Sequence('debian_distribution_id_seq'),
                ForeignKey('distribution.id'),
                primary_key=True)
    debian_security = Column(String(255))
    debian_volatile = Column(String(255))

    def getInfo(self):
        result = super(DebianDistribution, self).getInfo()
        result.update({
            "debian_security": self.debian_security,
            "debian_volatile": self.debian_volatile,
        })
        return result
