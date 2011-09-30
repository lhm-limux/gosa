#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common import Environment
from gosa.common.components import AMQPServiceProxy

class GosaHandler(object):
    def __init__(self):
        self.env = Environment.getInstance()
        self.proxyurl = self.env.config.get('fts.gosa', 'proxy_uri')
        #self.proxy = AMQPServiceProxy('amqps://cajus:tester@amqp.intranet.gonicus.de/org.gosa')
        self.proxy = AMQPServiceProxy(self.proxyurl)

    def getBootParams(self, address):
        return self.proxy.systemGetBootString(None, address)

#Environment.config="fts.conf"
#Environment.noargs=True
#FAI().systemGetBootParams("00:06:29:1F:75:95")
