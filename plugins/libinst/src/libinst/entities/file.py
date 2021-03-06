# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB

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
