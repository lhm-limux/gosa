# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB

class Architecture(Base, UseInnoDB):
    __tablename__ = 'arch'
    id = Column(Integer, Sequence('arch_id_seq'), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
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
