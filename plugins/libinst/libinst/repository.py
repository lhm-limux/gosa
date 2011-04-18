# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Sequence, Text, DateTime, Boolean, LargeBinary, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, backref, create_session, synonym
import os


Base = declarative_base()


class UseInnoDB(object):
    __table_args__ = {'mysql_engine': 'InnoDB'}


class Section(Base, UseInnoDB):
    __tablename__ = 'section'
    id = Column(Integer, Sequence('section_id_seq'), primary_key=True)
    description = Column(String(255))
    name = Column(String(255), unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class Component(Base, UseInnoDB):
    __tablename__ = 'component'
    id = Column(Integer, Sequence('component_id_seq'), primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(String(255))
    discriminator = Column(Integer(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class Architecture(Base, UseInnoDB):
    __tablename__ = 'arch'
    id = Column(Integer, Sequence('arch_id_seq'), primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(String(255))

    def __init__(self, name, **kwargs):
        self.name = name
        if 'description' in kwargs:
            self.description = kwargs.get('description')
        if 'id' in kwargs:
            self.id = id

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class Type(Base, UseInnoDB):
    __tablename__ = 'type'
    id = Column(Integer, Sequence('type_id_seq'), primary_key=True)
    name = Column(String(255), unique=True)
    description = Column(String(255))

    def __init__(self, name, description = ""):
        self.name = name
        self.description = description

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "description": self.description,
        }


class PackageFiles(Base, UseInnoDB):
    __tablename__ = 'package_files'
    package = Column(Integer, ForeignKey('package.id'), primary_key=True)
    file = Column(Integer, ForeignKey('file.id'), primary_key=True)


class File(Base, UseInnoDB):
    __tablename__ = 'file'
    id = Column(Integer, Sequence('file_id_seq'), primary_key=True)
    name = Column(String(255))
    size = Column(String(255))
    md5sum = Column(String(255))

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
            "size": self.size,
            "md5sum": self.md5sum,
        }


class Package(Base, UseInnoDB):
    __tablename__ = 'package'
    id = Column(Integer, Sequence('package_id_seq'), primary_key=True)
    name = Column(String(255))
    description = Column(String(255))
    section_id = Column(Integer, ForeignKey('section.id'))
    section = relationship(Section)
    component_id = Column(Integer, ForeignKey('component.id'))
    component = relationship(Component)
    arch_id = Column(Integer, ForeignKey('arch.id'))
    arch = relationship(Architecture)
    type_id = Column(Integer, ForeignKey('type.id'))
    type = relationship(Type)
    # pylint: disable-msg=E1101
    files = relationship(File, secondary=PackageFiles.__table__, backref=backref('package', uselist=True))
    version = Column(String(255))
    origin = Column(String(255))
    package_subtype = Column(String(50))
    __mapper_args__ = {'polymorphic_on': package_subtype}

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<package name='%s' arch='%s' type='%s' version='%s' />" % (self.name, self.arch.name, self.type.name, self.version)

    def getInfo(self):
        return {
            "name": self.name,
            "description": self.description,
            "section": self.section.name,
            "component": self.component.name,
            "arch": self.arch.name,
            "type": self.type.name,
            "files": None if not self.files else [file.getInfo() for file in self.files],
            "version": self.version,
            "origin": self.origin,
        }


class ReleasePackages(Base, UseInnoDB):
    __tablename__ = 'release_packages'
    release = Column(Integer, ForeignKey('release.id'), primary_key=True)
    package = Column(Integer, ForeignKey('package.id'), primary_key=True)


class Release(Base, UseInnoDB):
    __tablename__ = 'release'
    id = Column(Integer, Sequence('release_id_seq'), primary_key=True)
    name = Column(String(255), unique=True)
    parent_id = Column(Integer, ForeignKey('release.id'))
    # pylint: disable-msg=E1101
    packages = relationship(Package, secondary=ReleasePackages.__table__, backref=backref('releases', uselist=True))
    discriminator = Column(String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    def getInfo(self):
        return {
            "name": self.name,
            "parent": None if not self.parent else self.parent.getInfo(),
        }

    def _initDirs(self):
        pass

    def __repr__(self):
        return self.name


Release.parent = relationship(Release, remote_side=Release.id, uselist=False, backref=backref('children', uselist=True))


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
                    self.env.log.error("Could not create directory %s" % self.path)
                    raise

            for release in self.releases:
                release._initDirs()
        else:
            self.env.log.fatal("Distribution %s has no repository" % self.name)

    def _sync(self):
        pass


class Keyring(Base, UseInnoDB):
    __tablename__ = 'keyring'
    id = Column(Integer, Sequence('keyring_id_seq'), primary_key=True)
    name = Column(String(255))
    data = Column(LargeBinary())
    passphrase = Column(String(255))


class RepositoryDistributions(Base, UseInnoDB):
    __tablename__ = 'repository_distributions'
    distribution = Column(Integer, ForeignKey('distribution.id'), primary_key=True)
    repository = Column(Integer, ForeignKey('repository.id'), primary_key=True)


class Repository(Base, UseInnoDB):
    __tablename__ = 'repository'
    id = Column(Integer, Sequence('repository_id_seq'), primary_key=True)
    name = Column(String(255))
    path = Column(String(255), nullable=False, unique=True)
    keyring_id = Column(Integer, ForeignKey('keyring.id'))
    keyring = relationship(Keyring)
    # pylint: disable-msg=E1101
    distributions = relationship(Distribution, secondary=RepositoryDistributions.__table__, backref=backref('repository', uselist=False))

    def __repr__(self):
        return self.name if self.name is not None else self.id.__str__()

    def _initDirs(self):
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except:
                self.env.log.fatal("Could not create directory %s" % self.path)
                raise

        for distribution in self.distributions:
            distribution._initDirs()
