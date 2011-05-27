#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common.components.amqp_proxy import AMQPEventConsumer, \
    AMQPServiceProxy
from qpid.util import URL
from lxml import etree
import sys
import re
import ConfigParser
import MySQLdb

from GOforgeFetcher import GOforgeFetcher
from PhoneNumberResolver import PhoneNumberResolver


""" Not needed atm. Might be relevant for wrapping the database.
class ConnectionError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
"""


class AsteriskNotificationReceiver:
    TYPE_MAP = {'CallMissed': "Missed call",
                'CallEnded': "Call ended",
                'IncomingCall': "Incoming call"}

    def __init__(self, config, resolver, goforge):
        # Create event consumer
        self.consumer = AMQPEventConsumer(config['url'],
            xquery = """
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:AsteriskNotification
            """,
            callback = self.process)
        self.resolver = resolver
        self.goforge = goforge

        self.proxy = AMQPServiceProxy(config['url'])

    def __del__(self):
        if hasattr(self, 'consumer') and self.consumer is not None:
            del self.consumer

    def serve_forever(self):
        print "Running ..."
        while True:
            res = self.consumer.join()

    # Event callback
    def process(self, data):
        # for some reason we need to convert to string and back
        cstr = etree.tostring(data, pretty_print = True)
        dat = etree.fromstring(cstr)

        # retrive data from xml
        numbers = dat[0][2].text
        numbers = numbers.split(" ")
        n_from = numbers[0]
        numbers = dat[0][3].text
        numbers = numbers.split(" ")
        n_to = numbers[0]

        type = dat[0][0].text

        # resolve numbers
        i_from = self.resolver.resolve(n_from)
        i_to = self.resolver.resolve(n_to)

        # give some output to the console
        if type in self.TYPE_MAP:
            print self.TYPE_MAP[type]
        print "-----------"
        print "From:"
        print i_from
        print
        print "To:"
        print i_to
        print

        tickets = None
        if i_from is not None and i_from['resource'] == 'sugar' \
            and i_from['company_id'] != '':
            tickets = self.goforge.getTickets(i_from['company_id'])

        print "Open Tickets:"
        print tickets
        print

        if i_to is not None and i_to['resource'] == 'ldap':
            # Assemble caller info
            c_from = "From: "
            if i_from is None:
                c_from += n_from

            elif i_from['contact_name'] != "":
                c_from += i_from['contact_name']

                if i_from['company_name'] != "":
                    c_from += "(" + i_from['company_name'] + ")"

            elif i_from['company_name'] != "":
                c_from += i_from['company_name']
            c_from += "\n"

            msg = ""
            msg += c_from

            self.proxy.notifyUser(i_to['contact_id'], self.TYPE_MAP[type], msg)


class AMQPReceive:
    def __init__(self):
                # read configuration file
        conf = ConfigParser.RawConfigParser()
        conf.read("amqp_receive.cfg")

        # read replacement configuration
        replace = []
        items = conf.items("replace")
        for itm in items:
            res = re.search("^\"(.*)\",\"(.*)\"$", itm[1])
            res = re.search("^\"(.*)\"[\s]*,[\s]*\"(.*)\"$", itm[1])
            if not res == None:
                replace.append([res.group(1), res.group(2)])

        # set defaults for amqp config
        conf_amqp = {
            'url': 'amqps://localhost/org.gosa'}

        # set defaults for ldap config
        conf_ldap = {
            'host': 'localhost',
            'use_tls': '0'}

        # set defaults for sugar config
        conf_sugar = {
            'host': 'localhost',
            'user': 'root',
            'pass': '',
            'base': 'sugarcrm',
            'site_url': 'http://localhost/sugarcrm'}

        # set defaults for sugar config
        conf_goforge = {
            'host': 'localhost',
            'user': 'root',
            'pass': '',
            'base': 'sugarcrm'}

        # replace config from file
        if "sugar" in conf.sections():
            for key, val in conf.items("sugar"):
                conf_sugar[key] = val
        if "goforge" in conf.sections():
            for key, val in conf.items("goforge"):
                conf_goforge[key] = val
        if "amqp" in conf.sections():
            for key, val in conf.items("amqp"):
                conf_amqp[key] = val
        if "ldap" in conf.sections():
            for key, val in conf.items("ldap"):
                conf_ldap[key] = val

        # create phone number resolver
        resolver = PhoneNumberResolver(conf_sugar, conf_ldap,
                                       conf_goforge, replace)

        # create GOforge fetcher
        goforge = GOforgeFetcher(conf_goforge)

        # create amqp event receiver
        self.receiver = AsteriskNotificationReceiver(conf_amqp,
            resolver, goforge)

    def __del__(self):
        if hasattr(self, 'receiver') and self.receiver is not None:
            del self.receiver

    def serve_forever(self):
        try:
            self.receiver.serve_forever()
        except KeyboardInterrupt:
            print "Bye."


if __name__ == "__main__":
    print "AMQP Asterisk Event Receiver."

    plugin = AMQPReceive()
    plugin.serve_forever()
