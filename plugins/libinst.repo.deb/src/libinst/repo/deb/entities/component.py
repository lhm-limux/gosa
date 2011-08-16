# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.component import Component


class DebianComponent(Component, UseInnoDB):
    __mapper_args__ = {'polymorphic_identity': 'debian_component'}
