# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.package import Package


class ReleasePackages(Base, UseInnoDB):
    __tablename__ = 'release_packages'
    release = Column(Integer, ForeignKey('release.id'), primary_key=True)
    package = Column(Integer, ForeignKey('package.id'), primary_key=True)


class Release(Base, UseInnoDB):
    __tablename__ = 'release'
    id = Column(Integer, Sequence('release_id_seq'), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey('release.id'))
    # pylint: disable-msg=E1101
    packages = relationship(Package, secondary=ReleasePackages.__table__, backref=backref('releases', uselist=True))
    discriminator = Column(String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    def getInfo(self):
        return {
            "name": self.name,
            "parent": None if not self.parent else self.parent.getInfo(),
            "origin": None if not self.distribution.origin else self.distribution.origin,
        }

    def _initDirs(self):
        pass

    def __repr__(self):
        return self.name


Release.parent = relationship(Release, remote_side=Release.id, uselist=False, backref=backref('children', uselist=True))
