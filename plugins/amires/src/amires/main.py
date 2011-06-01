#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pkg_resources
import gettext
from lxml import etree
from gosa.common.env import Environment
from gosa.common.utils import parseURL, makeAuthURL
from gosa.common.components.amqp_proxy import AMQPEventConsumer, \
    AMQPServiceProxy

#TODO: modularize later on, maybe two fetcher: sugar/goforge
from amires.modules.goforge_sect import GOforgeSection, MainSection

# Set locale domain
t = gettext.translation('messages', resource_filename("amires", "locale"),
        fallback=True)
_ = t.ugettext


class AsteriskNotificationReceiver:
    TYPE_MAP = {'CallMissed': _("Missed call"),
                'CallEnded': _("Call ended"),
                'IncomingCall': _("Incoming call")}

    resolver = {}

    def __init__(self):
        self.env = env = Environment.getInstance()

        # Evaluate AMQP URL
        user = env.config.getOption("id", "amqp", default=None)
        if not user:
            user = env.uuid
        password = env.config.getOption("key", "amqp")
        url = parseURL(makeAuthURL(env.config.getOption('url', 'amqp'), user, password))
        if url['path']:
            self.url = url['source']
        else:
            domain = self.env.config.getOption('domain', 'amqp', default="org.gosa")
            self.url = "/".join([url['source'], domain])

        # Load resolver
        for entry in pkg_resources.iter_entry_points("phone.resolver"):
            module = entry.load()
            self.resolver[module.__name__] = {
                    'object': module(),
                    'priority': module.priority,
            }

        #TODO: make this a dynamically loaded fetcher module
        self.goforge = GOforgeSection()
        self.mainsection = MainSection()

        # Create event consumer
        self.consumer = AMQPEventConsumer(self.url,
            xquery = """
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:AsteriskNotification
            """,
            callback = self.process)

        self.proxy = AMQPServiceProxy(self.url)

    def __del__(self):
        if hasattr(self, 'consumer') and self.consumer is not None:
            del self.consumer

    def serve(self):
        self.env.log.info("Service running...")
        while True:
            self.consumer.join()

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

        etype = dat[0][0].text

        # Resolve numbers with all resolvers, sorted by priority
        i_from = None
        i_to = None

        for mod, info in sorted(self.resolver.iteritems(),
                key=lambda k: k[1]['priority']):
            if not i_from:
                i_from = info['object'].resolve(n_from)
            if not i_to:
                i_to = info['object'].resolve(n_to)
            if i_from and i_to:
                break

        # Back to original numbers
        if not i_from:
            i_from = {'contact_phone': n_from, 'contact_name': "Unknown"}
        if not i_to:
            i_to = {'contact_phone': n_to, 'contact_name': "Unknown"}

        # give some output to the console
        if etype in self.TYPE_MAP:
            print self.TYPE_MAP[etype]
        print "-----------"
        print "From:"
        print i_from
        print
        print "To:"
        print i_to
        print


        tickets = None
        """
        if 'resource' in i_from and i_from['resource'] == 'sugar' \
            and i_from['company_id'] != '':
            tickets = self.goforge.getTickets(i_from['company_id'])
        """

        print "Open Tickets:"
        print tickets
        print

        if 'contact_id' in i_to:
            # Assemble caller info
            c_from = "From: "
            if i_from is None:
                c_from += n_from

            elif i_from['contact_name'] != "":
                c_from += i_from['contact_name']

                if i_from['company_name'] != "":
                    c_from += "(" + i_from['company_name'] + ")"

            else:
                c_from += "Unknown"

            c_from += "\n"

            msg = ""
            msg += c_from

            # render bubble with BubbleSectionBuilders
            msg = self.mainsection.getHTML(i_from)
            msg += self.goforge.getHTML(i_from)
            print msg

            self.proxy.notifyUser(i_to['contact_id'], self.TYPE_MAP[etype],
                    unicode(msg, 'utf-8'))

def main():
    # For usage inside of __main__ we need a dummy initialization
    # to load the environment, because there's no one who's doing
    # it for us...
    Environment.config = "/etc/gosa/config"
    Environment.noargs = True
    env = Environment.getInstance()

    # Load receiver and serve forever
    handler = AsteriskNotificationReceiver()
    try:
        handler.serve()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
