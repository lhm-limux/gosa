# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities.architecture import Architecture
from libinst.entities.component import Component
from libinst.entities.file import File
from libinst.entities.section import Section
from libinst.entities.type import Type

from libinst.entities import Base, UseInnoDB


class PackageFiles(Base, UseInnoDB):
    __tablename__ = 'package_files'
    package = Column(Integer, ForeignKey('package.id'), primary_key=True)
    file = Column(Integer, ForeignKey('file.id'), primary_key=True)


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
            "section": None if not self.section else self.section.name,
            "component": self.component.name,
            "arch": self.arch.name,
            "type": self.type.name,
            "files": None if not self.files else [file.getInfo() for file in self.files],
            "version": self.version,
            "origin": self.origin,
        }
