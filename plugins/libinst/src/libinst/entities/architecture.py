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

from libinst.entities import Base, UseInnoDB

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
