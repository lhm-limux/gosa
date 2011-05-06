"""
This code is part of GOsa (http://www.gosa-project.org)
Copyright (C) 2009, 2010 GONICUS GmbH

ID: $$Id: command.py 248 2010-06-22 14:06:48Z cajus $$

This is a small collection of useful functions.

See LICENSE for more information about the licensing.
"""
import re
import os
import time
import StringIO
from tokenize import generate_tokens
from token import STRING
import traceback
import urllib
import subprocess
from subprocess import Popen, PIPE
from qpid.messaging.constants import AMQP_PORT, AMQPS_PORT
from urlparse import urlparse
from lxml import etree
from pkg_resources import *
from datetime import datetime

def stripNs(data):
    p = re.compile(r'^\{[^\}]+\}(.*)$')
    return p.match(data).group(1)

def makeAuthURL(url, user, password):
    o = urlparse(url)
    return "%s://%s:%s@%s%s" % (o.scheme, user, password, o.netloc, o.path)

def parseURL(url):
    if not url:
        return None

    source = url
    url = urlparse(url)

    # Load parts and extend if not provided
    # pylint: disable-msg=E1101
    scheme, user, password, host, port, path = url.scheme, url.username, url.password, url.hostname, url.port, url.path[1:]
    if scheme[0:4] == 'amqp':
        if scheme == 'amqp':
            port = AMQP_PORT if not port else port
        else:
            port = AMQPS_PORT if not port else port

        path = None if path == "" else path
        url = '%s/%s@%s:%s' % (user, password, host, port)
        ssl = 'tcp+tls' if scheme[-1] == 's' else 'tcp'
    else:
        if scheme == 'http':
            port = 80 if not port else port
        else:
            port = 443 if not port else port

        path = 'rpc' if path == "" else path
        url = '%s://%s:%s@%s:%s/%s' % (scheme, user, password, host, port, path)
        ssl = 'tcp+ssl' if scheme[-1] == 's' else 'tcp'

    return {'source':source,
        'scheme':scheme,
        'user':user,
        'password':password,
        'host':host,
        'port':int(port),
        'path':path,
        'transport':ssl,
        'url':url}

def buildXMLSchema(resource, prefix, stylesheet):
    """ Assembles single schema files to a final schema using the stylesheet """
    res = ''

    try:
        # Initialize prefix and get filenames
        real_prefix = resource_filename(resource, prefix) + os.sep
        if os.sep == "\\":
            real_prefix = "file:///" + "/".join(real_prefix.split("\\"))

        files = [ev for ev in resource_listdir(resource, prefix)
            if ev[-4:] == '.xsd']
        stylesheet = resource_filename(resource, stylesheet)

        # Build a tree of all event paths
        eventsxml = '<events prefix="' + urllib.quote(real_prefix) + '">'
        for file in files:
            eventsxml += '<path>' + file + '</path>'
        eventsxml += '</events>'
        eventsxml = StringIO.StringIO(eventsxml)

        # Parse the string with all event paths
        xml_doc = etree.parse(eventsxml)

        # Parse XSLT stylesheet and create a transform object
        xslt_doc = etree.parse(stylesheet)
        transform = etree.XSLT(xslt_doc)

        # Transform the tree of all event paths into the final XSD
        res = transform(xml_doc)
    except (IOError), e:
        traceback.print_exc()

    return str(res)

def N_(message):
    """
    Function to be used for deferred translations. Mark strings that should
    exist as a translation, but not be translated in the moment as N_('text').

    @type message: str
    @ivar message: text to be marked as a translation
    """
    return message

def get_timezone_delta():
    """
    Function to estimate the local timezone shift.

    @rtype str
    @return String in the format [+-]hours:minutes
    """
    timestamp = time.mktime(datetime.now().timetuple())
    timeDelta = datetime.fromtimestamp(timestamp) - datetime.utcfromtimestamp( timestamp )
    seconds = timeDelta.seconds
    return "%s%02d:%02d" % ("-" if seconds < 0 else "+", abs(seconds//3600), abs(seconds%60))

def locate(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath = os.path.dirname(program)
    if fpath and is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def dmi_system(item, data=None):
    return None

# Re-define dmi_system depending on capabilites
try:
    import dmidecode
    dmidecode.clear_warnings()

    def dmi_system(item, data=None):
        if not data:
            data = dmidecode.system()
            dmidecode.clear_warnings()
        item = item.lower()

        for key, value in data.iteritems():
            if item == key.lower():
                return value
            if isinstance(value, dict):
                value = dmi_system(item, value)
                if value:
                    return value

        return None
except:

    for ext in ["dmidecode", "dmidecode.exe"]:
        if locate(ext):
            def dmi_system(item, data=None):
                cmd = [ext, '-s', 'system-uuid']
                p = Popen(cmd, stdout=PIPE, stderr=PIPE)
                (stdout, stderr) = p.communicate()
                return stdout.strip()

            break

def f_print(data):
    if not isinstance(data, basestring):
        return data[0] % tuple(data[1:])
    else:
        return data

def repr2json(string):
    g = generate_tokens(StringIO.StringIO(string).readline)

    result = ""
    for toknum, tokval, _, _, _  in g:
        if toknum == STRING:
            tokval = '"' + tokval[1:-1].replace('"', r'\"') + '"'

        result += tokval

    return result
