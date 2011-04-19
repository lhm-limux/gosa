# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

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
