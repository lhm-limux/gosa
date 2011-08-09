# -*- coding: utf-8 -*-
from lxml.builder import ElementMaker

def EventMaker():
    """
    Returns the even skeleton object which can be directly used for
    extending with event data.
    """
    return ElementMaker(namespace="http://www.gonicus.de/Events", nsmap={None:"http://www.gonicus.de/Events"})
