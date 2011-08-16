# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB

class Component(Base, UseInnoDB):
    __tablename__ = 'component'
    id = Column(Integer, Sequence('component_id_seq'), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
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
