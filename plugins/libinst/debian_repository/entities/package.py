# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence, Text
from sqlalchemy.orm import relationship, backref

from libinst.entities.package import Package

from libinst.entities import Base, UseInnoDB
from debian_repository.entities.priority import DebianPriority


class DebianPackage(Package, UseInnoDB):
    __tablename__ = 'debian_package'
    __mapper_args__ = {'polymorphic_identity': 'debian_package'}
    id = Column(Integer,
                Sequence('debian_package_id_seq'),
                ForeignKey('package.id'),
                primary_key=True)
    package = relationship(Package)
    source = Column(String(255))
    maintainer = Column(String(255))
    installed_size = Column(String(255))
    depends = Column(Text)
    build_depends = Column(Text)
    format = Column(Text)
    standards_version = Column(Text)
    recommends = Column(Text)
    suggests = Column(Text)
    provides = Column(Text)
    priority_id = Column(Integer, ForeignKey('debian_priority.id'))
    priority = relationship(DebianPriority)
    long_description = Column(Text)

    def __repr__(self):
        return super(DebianPackage, self).__repr__()

    def getInfo(self):
        result = super(DebianPackage, self).getInfo()
        result.update({
            "source": self.source,
            "maintainer": self.maintainer,
            "installed_size": self.installed_size,
            "depends": self.depends,
            "build_depends": self.build_depends,
            "format": self.format,
            "standards_version": self.standards_version,
            "recommends": self.recommends,
            "suggests": self.suggests,
            "provides": self.provides,
            # pylint: disable-msg=E1101
            "priority": None if not self.priority else self.priority.name,
            "long_description": self.long_description,
        })
        return result
