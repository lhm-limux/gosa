#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys
from ZSI import wstools, ServiceProxy
from ZSI.wstools.WSDLTools import *
from httplib import HTTPConnection


class AmqpConnection(HTTPConnection):
    __amqp = None
    __debuglevel = 0


    # The connection is initialized with an AmqpWorker instance
    def __init__(amqp):
        self.__amqp = amqp


    def request(method, url, body, headers):
        """ This will send a request to the server using the HTTP request
            method method and the selector url. If the body argument is
            present, it should be a string of data to send after the headers
            are finished. The header Content-Length is automatically set to
            the correct value. The headers argument should be a mapping of
            extra HTTP headers to send with the request. """
        print method
        print url
        print body
        print headers


    def getresponse():
        print "getresponse"
        # fill HTTPResponse instance


    def set_debuglevel(level):
        self.__debuglevel = level


    def connect():
        print "connect"


    def close():
        print "close"


    def putrequest(request, selector, skip_host, skip_accept_encoding):
        print putrequest


    def putheader(header, argument, ...):
        print putheader


    def endheaders():
        print headers


    def send(data):
        print "data"


# Dummy functions ####

def add(self, x, y):
    return x + y


def pow(self, x):
    return x ** 2

######################



def main():

    # How to programatically create a WSDL ###################################
    ws = WSDL("urn:gosa.wsdl")

    gp = ws.addPortType("addPortType")

    mi = ws.addMessage("addInput")
    mi.addPart("x", ("http://www.w3.org/1999/XMLSchema", "integer"))
    mi.addPart("y", ("http://www.w3.org/1999/XMLSchema", "integer"))
    mo = ws.addMessage("addOutput")
    mo.addPart("result", ("http://www.w3.org/1999/XMLSchema", "integer"))

    op = gp.addOperation("add")
    op.setInput("addInput")
    op.setOutput("addOutput")

    bd = ws.addBinding("addBinding", ("urn:gosa.wsdl", "addPortType"))
    bd.addExtension(SoapBinding("http://schemas.xmlsoap.org/soap/http", "rpc"))
    opb = bd.addOperationBinding("add")
    opb.addExtension(SoapOperationBinding("add"))
    opb.addInputBinding(SoapBodyBinding("encoded", namespace="http://schemas.xmlsoap.org/wsdl/soap/"))
    opb.addOutputBinding(SoapBodyBinding("encoded", namespace="http://schemas.xmlsoap.org/wsdl/soap/"))

    sv = ws.addService("addService")
    svp = sv.addPort("addPort", ("urn:gosa.wsdl", "addBinding"))
    svp.addExtension(SoapAddressBinding("command"))

    ws.toDom()
    #print ws.document.toprettyxml()
    ##########################################################################


    # How to inspect WSDL ####################################################
    #wsdl = wstools.WSDLTools.WSDLReader().loadFromString(ws.document.toxml())
    #service = wsdl.services[0]
    #for port in service.ports:
    #    for item in port.getPortType().operations:
    #        callinfo = wstools.WSDLTools.callInfoFromWSDL(port, item.name)
    #        ret = "(void)"
    #        if len(callinfo.outparams) > 0:
    #            ns, type = callinfo.outparams[0].type
    #            ret = "(%s)" % type
    #        params = []
    #        for param in callinfo.inparams:
    #            ns, type = param.type
    #            params.append("%s %s" % (type, param.name))

    #        print ("%s " + callinfo.methodName + "(%s)") % (ret, ", ".join(params))
    ##########################################################################


    # How to use WSDL, AMQP and to ServiceProxy
    wsdl = 'http://dyn-muc-50/gosa.wsdl'
    proxy = ServiceProxy(wsdl, transport=AmqpConnection(None))
    print proxy.add(5, 6)


if __name__ == '__main__':
    main()
