# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UseInnoDB(object):
    __table_args__ = {'mysql_engine': 'InnoDB'}

__import__('pkg_resources').declare_namespace(__name__)

