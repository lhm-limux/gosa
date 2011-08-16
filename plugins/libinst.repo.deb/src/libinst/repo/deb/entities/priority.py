# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB


class DebianPriority(Base, UseInnoDB):
    __tablename__ = 'debian_priority'
    id = Column(Integer, Sequence('debian_priority_id_seq'), primary_key=True)
    name = Column(String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
        }
