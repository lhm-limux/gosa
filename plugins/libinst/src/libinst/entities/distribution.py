# -*- coding: utf-8 -*-
import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence, Boolean, DateTime
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.architecture import Architecture
from libinst.entities.component import Component
from libinst.entities.release import Release
from libinst.entities.section import Section
from libinst.entities.type import Type

class DistributionReleases(Base, UseInnoDB):
    __tablename__ = 'distribution_releases'
    distribution = Column(Integer, ForeignKey('distribution.id'), primary_key=True)
    release = Column(Integer, ForeignKey('release.id'), primary_key=True)


class DistributionComponents(Base, UseInnoDB):
    __tablename__ = 'distribution_components'
    distribution = Column(Integer, ForeignKey('distribution.id'), primary_key=True)
    component = Column(Integer, ForeignKey('component.id'), primary_key=True)


class DistributionArchitectures(Base, UseInnoDB):
    __tablename__ = 'distribution_architectures'
    distribution = Column(Integer, ForeignKey('distribution.id'), primary_key=True)
    architecture = Column(Integer, ForeignKey('arch.id'), primary_key=True)


class DistributionSections(Base, UseInnoDB):
    __tablename__ = 'distribution_sections'
    distribution = Column(Integer, ForeignKey('distribution.id'), primary_key=True)
    section = Column(Integer, ForeignKey('section.id'), primary_key=True)


class Distribution(Base, UseInnoDB):
    __tablename__ = 'distribution'
    id = Column(Integer, Sequence('distribution_id_seq'), primary_key=True)
    name = Column(String(255))
    # pylint: disable-msg=E1101
    releases = relationship(Release, secondary=DistributionReleases.__table__, backref=backref('distribution', uselist=False))
    type_id = Column(Integer, ForeignKey('type.id'))
    type = relationship(Type)
    origin = Column(String(255))
    managed = Column(Boolean) # Is managed? -> master : mirror
    # pylint: disable-msg=E1101
    components = relationship(Component, secondary=DistributionComponents.__table__)
    # pylint: disable-msg=E1101
    architectures = relationship(Architecture, secondary=DistributionArchitectures.__table__)
    # pylint: disable-msg=E1101
    sections = relationship(Section, secondary=DistributionSections.__table__)
    discriminator = Column('discriminator', String(50))
    path = Column(String(255))
    last_updated = Column(DateTime)
    #base_installation_method = Column(String(255))
    installation_method = Column(String(255))
    mirror_sources = Column(Boolean, default=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    def __init__(self, name):
        self.name = name
        self.log = logging.getLogger(__name__)

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "type": None if not self.type else self.type.getInfo(),
            "origin": self.origin,
            "managed": self.managed,
            "releases": None if not self.releases else [release.getInfo() for release in self.releases],
            "components": None if not self.components else [component.getInfo() for component in self.components],
            "architectures": None if not self.architectures else [architecture.getInfo() for architecture in self.architectures],
            "sections": None if not self.sections else [section.getInfo() for section in self.sections],
            "path": self.path,
            "last_updated": self.last_updated,
            "installation_method": self.installation_method,
            #"base_installation_method": self.base_installation_method,
            "mirror_sources": self.mirror_sources,
        }

    def _initDirs(self):
        if self.repository:
            self.path = self.repository.path + os.sep + self.name
            if not os.path.exists(self.path):
                try:
                    os.makedirs(self.path)
                except:
                    self.log.error("Could not create directory %s" % self.path)
                    raise

            for release in self.releases:
                release._initDirs()
        else:
            self.log.fatal("Distribution %s has no repository" % self.name)

    def _sync(self):
        pass
