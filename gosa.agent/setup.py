#!/usr/bin/env python
from setuptools import setup, find_packages
import os
import platform

try:
    from babel.messages import frontend as babel
except:
    pass

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README')).read()
CHANGES = open(os.path.join(here, 'CHANGES')).read()


setup(
    name = "gosa.agent",
    version = "3.0",
    author = "Cajus Pollmeier",
    author_email = "pollmeier@gonicus.de",
    description = "Identity-, system- and configmanagement middleware",
    long_description = README + "\n\n" + CHANGES,
    keywords = "system config management ldap groupware",
    license = "LGPL",
    url = "http://www.gosa-project.org",
    classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: System :: Systems Administration',
        'Topic :: System :: Systems Administration :: Authentication/Directory',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Monitoring',
    ],

    download_url = "http://oss.gonicus.de/pub/gosa",
    packages = find_packages('src', exclude=['examples', 'tests']),
    package_dir={'': 'src'},
    namespace_packages = ['gosa'],

    include_package_data = True,
    package_data = {
        'gosa.agent': ['data/agent.conf', 'data/events', 'data/objects'],
        'gosa.agent.plugins.goto': ['data/events'],
    },

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = [
        'nose==0.11.1',
        'NoseXUnit',
        'pylint',
        ],
    install_requires = [
        'gosa.common',
        'webob',
        'paste',
        'netaddr',
        'smbpasswd',
        'python_daemon',
        'lockfile',
        'dumbnet',
        'pycrypto',
        'unidecode',
        'sqlalchemy',
        ],
    dependency_links = [
        'http://oss.gonicus.de/pub/gosa/eggs',
        ],

    # Not installable this way:
    # dumbnet

    entry_points = """
        [console_scripts]
        gosa-agent = gosa.agent.main:main

        [gosa.modules]
        gosa-agent.command = gosa.agent.command:CommandRegistry
        gosa-agent.amqp_service = gosa.agent.amqp_service:AMQPService
        gosa-agent.httpd = gosa.agent.httpd:HTTPService
        gosa-agent.scheduler = gosa.agent.scheduler:SchedulerService
        gosa-agent.acl = gosa.agent.acl:ACLResolver
        gosa-agent.jsonrpc_service = gosa.agent.jsonrpc_service:JSONRPCService
        gosa-agent.jsonrpc_om = gosa.agent.jsonrpc_objects:JSONRPCObjectMapper
        gosa-agent.plugins.samba.utils = gosa.agent.plugins.samba.utils:SambaUtils
        gosa-agent.plugins.misc.utils = gosa.agent.plugins.misc.utils:MiscUtils
        gosa-agent.plugins.gravatar.utils = gosa.agent.plugins.gravatar.utils:GravatarUtils
        gosa-agent.plugins.goto.network = gosa.agent.plugins.goto.network:NetworkUtils
        gosa-agent.plugins.goto.client_service = gosa.agent.plugins.goto.client_service:ClientService

        [gosa.object.backend]
        backend.ldap = gosa.agent.objects.backend.back_ldap:LDAP

        [gosa.object.comparator]
        comparator.like = gosa.agent.objects.comparator.strings:Like
        comparator.regex = gosa.agent.objects.comparator.strings:RegEx
        comparator.isstring = gosa.agent.objects.comparator.strings:isString
        comparator.stringlength = gosa.agent.objects.comparator.strings:stringLength
        comparator.equals = gosa.agent.objects.comparator.basic:Equals
        comparator.greater = gosa.agent.objects.comparator.basic:Greater
        comparator.smaller = gosa.agent.objects.comparator.basic:Smaller

        [gosa.object.filter]
        filter.tounixtime = gosa.agent.objects.filter.timestamp:ToUnixTime
        filter.fromunixtime = gosa.agent.objects.filter.timestamp:FromUnixTime
        filter.concatstring = gosa.agent.objects.filter.strings:ConcatString
        filter.replace = gosa.agent.objects.filter.strings:Replace
        filter.stringToTime = gosa.agent.objects.filter.strings:StringToTime
        filter.stringToDate = gosa.agent.objects.filter.strings:StringToDate
        filter.dateToString = gosa.agent.objects.filter.strings:DateToString
        filter.timeToString = gosa.agent.objects.filter.strings:TimeToString
        filter.sambahash = gosa.agent.plugins.samba.utils:SambaHash
        filter.target = gosa.agent.objects.filter.basic:Target
        filter.setvalue = gosa.agent.objects.filter.basic:SetValue
        #filter.loadattr = gosa.agent.objects.filter.basic:LoadAttr
        #filter.saveattr = gosa.agent.objects.filter.basic:SaveAttr
        filter.clear = gosa.agent.objects.filter.basic:Clear

        [gosa.object.operator]
        operator.and = gosa.agent.objects.operator.bool:And
        operator.or = gosa.agent.objects.operator.bool:Or
        operator.not = gosa.agent.objects.operator.bool:Not
    """,
)
