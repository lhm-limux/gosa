#!/usr/bin/env python
from setuptools import setup, find_packages
import os
import platform

try:
    from babel.messages import frontend as babel
except:
    pass

setup(
    name = "amires",
    version = "0.1",
    author = "Dennis Radon",
    author_email = "radon@gonicus.de",
    description = "Event handling for Asterisk based setups",
    long_description = "TBD",
    keywords = "amqp telephony notification",
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

    packages = find_packages('src', exclude=['examples', 'tests']),
    package_dir={'': 'src'},

    include_package_data = True,
    package_data = {
        'gosa.common': ['data/AsteriskNotification.xsd'],
    },

    install_requires = [
        'gosa.agent',
        ],

    entry_points = """
        [console_scripts]
        ami-resolver = amires.main:main

        #[gosa.modules]
        #ami.resolver = amires.main:AMIResolver

        [phone.resolver]
        res.ldap = amires.modules.ldap_res:LDAPNumberResolver
        res.sugar = amires.modules.sugar_res:SugarNumberResolver
        #res.telekom = amires.modules.telekom_res:TelekomNumberResolver
        res.xml = amires.modules.xml_res:XMLNumberResolver
        #res.static = amires.modules.static_res:StaticResolver

        [notification.fetcher]
        #fetch.sugar = amires.modules.sugar_res:SugarFetcher
        fetch.goforge = amires.modules.goforge_res:GOForgerFetcher
    """,
)
