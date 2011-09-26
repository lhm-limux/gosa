#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common import Environment
from gosa.common.components import AMQPServiceProxy

class GosaHandler(object):
    def __init__(self):
        self.proxy = AMQPServiceProxy('amqps://cajus:tester@amqp.intranet.gonicus.de/org.gosa')

    def getBootParams(self, address):
        return self.proxy.systemGetBootString(None, address)

#Environment.config="fts.conf"
#Environment.noargs=True
#env = Environment.getInstance()
#FAI().systemGetBootParams("00:06:29:1F:75:95")
