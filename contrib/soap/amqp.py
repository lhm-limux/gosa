# -*- coding: utf-8 -*-
import sys
import os
import traceback
from httplib import HTTPConnection
from qpid.messaging import *
from qpid.messaging.util import auto_fetch_reconnect_urls
from qpid.log import enable, DEBUG, WARN
from qpid.util import URL, connect
from qpid.concurrency import synchronized

_UNKNOWN = 'UNKNOWN'

class AMQPNotImplemented(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class AMQPConnection(HTTPConnection):
    __amqp = None
    __msg = None
    __id = None
    handler = None

    # The connection should be initialized with an AMQPWorker instance later on
    def __init__(self, host, port=None, strict=None, conn=None, address='command.exec'):
        self.__conn = conn
        self.__session = conn.session(str(uuid4()))
        self.__sender = self.__session.sender(address)
        self.__receiver = self.__session.receiver('reply-%s; {create:always, delete:always}' % self.__session.name)


    def request(self, method, url, body=None, headers={}):
        raise AMQPNotImplemented("AMQPConnection.request is not implemented")


    def getresponse(self):
        msg = self.__receiver.fetch()
        self.__session.acknowledge()
        return AMQPResponse(msg)


    # We've global debugging, no need for levels here
    def set_debuglevel(self, level):
        pass


    def connect(self):
        pass


    def close(self):
        pass


    def putrequest(self, request, selector, skip_host= 0, skip_accept_encoding= 0):
        self.__msg = Message()
        self.__msg.reply_to = 'reply-%s' % self.__session.name


    def putheader(self, header, *argument):
        #self.__msg.header = value
        #putheader(Content-Length, ('500',))
        #putheader(Content-Type, ('text/xml; charset="utf-8"',))
        #putheader(SOAPAction, (u'"add"',))
        pass


    def endheaders(self):
        pass


    def send(self, data):
        self.__msg.content = data
        self.__sender.send(self.__msg)


class AMQPResponse:

    def __init__(self, msg):
        self.msg = AMQPDummyMessage()
        self.status = _UNKNOWN  # Status-Code
        self.reason = _UNKNOWN  # Reason-Phrase
        self.__msg = msg


    def getheader(self, name, default=None):
        if self.msg is None:
            raise httplib.ResponseNotReady()
        return self.msg.getheader(name, default)


    def read(self, amt=None):
        return self.__msg.content


class AMQPDummyMessage:
    # Aus putheader(Content-Type, ('text/xml; charset="utf-8"',))
    type = "text/xml"
    
    def getallmatchingheaders(self, header):
        return []

