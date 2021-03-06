#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pkg_resources
import gettext
import re
import logging
from lxml import etree
from zope.interface import implements
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.common.utils import parseURL, makeAuthURL
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.amqp import EventConsumer
from gosa.common.components import AMQPServiceProxy

# Set locale domain
t = gettext.translation('messages', pkg_resources.resource_filename("amires", "locale"),
        fallback=False)
_ = t.ugettext


class AsteriskNotificationReceiver(object):
    implements(IInterfaceHandler)
    _priority_ = 99

    TYPE_MAP = {'CallMissed': _("Missed call"),
                'CallEnded': _("Call ended"),
                'IncomingCall': _("Incoming call")}

    resolver = {}
    renderer = {}

    def __init__(self):
        self.env = env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.log.debug("initializing asterisk number resolver")

        # Load resolver
        for entry in pkg_resources.iter_entry_points("phone.resolver"):
            module = entry.load()
            self.log.debug("loading resolver module '%s'" % module.__name__)
            obj = module()
            self.resolver[module.__name__] = {
                    'object': obj,
                    'priority': obj.priority,
            }

        # Load renderer
        for entry in pkg_resources.iter_entry_points("notification.renderer"):
            module = entry.load()
            self.log.debug("loading renderer module '%s'" % module.__name__)
            self.renderer[module.__name__] = {
                    'object': module(),
                    'priority': module.priority,
            }

    def serve(self):
        self.log.info("listening for asterisk events...")
        amqp = PluginRegistry.getInstance('AMQPHandler')
        EventConsumer(self.env,
            amqp.getConnection(),
            xquery="""
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:AsteriskNotification
            """,
            callback=self.process)

        self.__cr = PluginRegistry.getInstance("CommandRegistry")

    # Event callback
    def process(self, data):

        # for some reason we need to convert to string and back
        cstr = etree.tostring(data, pretty_print = True)
        dat = etree.fromstring(cstr)

        event = {}
        for t in dat[0]:
            tag = re.sub(r"^\{.*\}(.*)$", r"\1", t.tag)
            if t.tag == 'From':
                event[tag] = t.text.split(" ")[0]
            else:
                event[tag] = str(t.text)

        # Resolve numbers with all resolvers, sorted by priority
        i_from = None
        i_to = None

        for mod, info in sorted(self.resolver.iteritems(),
                key=lambda k: k[1]['priority']):
            if not i_from:
                i_from = info['object'].resolve(event['From'])
            if not i_to:
                i_to = info['object'].resolve(event['To'])
            if i_from and i_to:
                break

        # Fallback to original number if nothing has been found
        if not i_from:
            i_from = {'contact_phone': event['From'], 'contact_name': event['From'],
                    'company_name': None, 'resource': 'none'}
        if not i_to:
            i_to = {'contact_phone': event['To'], 'contact_name': event['To'],
                    'company_name': None, 'resource': 'none'}

        # Render messages
        to_msg = from_msg = ""
        for mod, info in sorted(self.renderer.iteritems(),
                key=lambda k: k[1]['priority']):

            if 'ldap_uid' in i_to and i_to['ldap_uid']:
                to_msg += info['object'].getHTML(i_from, event)
                to_msg += "\n\n"

            if 'ldap_uid' in i_from and i_from['ldap_uid'] and event['Type'] == 'CallEnded':
                from_msg += info['object'].getHTML(i_to, event)
                from_msg += "\n\n"

        # Send from/to messages as needed
        amqp = PluginRegistry.getInstance('AMQPHandler')
        if from_msg:
            self.__cr.dispatch(amqp.url['user'], None, "notifyUser",
                i_from['ldap_uid'], self.TYPE_MAP[event['Type']],
                from_msg.strip())

        if to_msg:
            self.__cr.dispatch(amqp.url['user'], None, "notifyUser",
                    i_to['ldap_uid'], self.TYPE_MAP[event['Type']],
                    to_msg.strip())
