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
    version = "0.1",
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
        'gosa.agent': ['data/agent.conf'],
    },

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = [
        'nose',
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
        gosa-agent.jsonrpc_service = gosa.agent.jsonrpc_service:JSONRPCService
        gosa-agent.jsonrpc_om = gosa.agent.jsonrpc_service:JSONRPCObjectMapper
        gosa-agent.plugins.samba.utils = gosa.agent.plugins.samba.utils:SambaUtils
        gosa-agent.plugins.misc.utils = gosa.agent.plugins.misc.utils:MiscUtils
        gosa-agent.plugins.gravatar.utils = gosa.agent.plugins.gravatar.utils:GravatarUtils
        gosa-agent.plugins.goto.network = gosa.agent.plugins.goto.network:NetworkUtils
        gosa-agent.plugins.goto.client_service = gosa.agent.plugins.goto.client_service:ClientService
    """,
)
