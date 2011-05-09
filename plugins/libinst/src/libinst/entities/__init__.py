# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: __init__.py 487 2010-08-10 07:34:06Z cajus $$

 See LICENSE for more information about the licensing.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UseInnoDB(object):
    __table_args__ = {'mysql_engine': 'InnoDB'}

__import__('pkg_resources').declare_namespace(__name__)

