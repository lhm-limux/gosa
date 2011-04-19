# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.release import Release


class ConfigItemReleases(Base, UseInnoDB):
    __tablename__ = 'config_item_releases'
    config_item = Column(Integer, ForeignKey('config_item.id'), primary_key=True)
    release = Column(Integer, ForeignKey('release.id'), primary_key=True)


class ConfigItem(Base, UseInnoDB):
    __tablename__ = 'config_item'
    id = Column(Integer, Sequence('config_item_id_seq'), primary_key=True)
    name = Column(String(255))
    item_type = Column(String(255))
    path = Column(String(255))
    parent_id = Column(Integer, ForeignKey('config_item.id'))
    # pylint: disable-msg=E1101
    release = relationship(Release, secondary=ConfigItemReleases.__table__, backref=backref('config_items'))

    def getPath(self):
        result = []

        if self.parent:
            result.append(self.parent.getPath())

        return "/" + os.sep.join(result + [self.name]).strip("/")

    def __repr__(self):
        return "%s -> %s (%s)" % (self.release, self.name, self.item_type)

    def getInfo(self):
        return {
            "name": self.name,
            "item_type": self.item_type,
            "path": self.path,
            "release": None if not self.release else self.relase.name,
        }

ConfigItem.parent = relationship(ConfigItem, remote_side=ConfigItem.id, uselist=False, backref=backref('children', uselist=True))
# pylint: disable-msg=E1101
ConfigItem.__table__.append_constraint(UniqueConstraint('item_type', 'path'))
