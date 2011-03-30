# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: event.py 608 2010-08-16 08:12:35Z cajus $$

 This is the Event object. It constructs events to be sent thru the
 org.gosa.event topics.

 See LICENSE for more information about the licensing.
"""
from lxml.builder import ElementMaker

def EventMaker():
    return ElementMaker(namespace="http://www.gonicus.de/Events", nsmap={None:"http://www.gonicus.de/Events"})
