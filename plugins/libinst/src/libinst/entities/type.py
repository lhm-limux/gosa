# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB


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
