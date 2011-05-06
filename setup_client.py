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


client_install_requires = [
    'gosa.common',
    'netaddr',
    'netifaces',
    'python_dateutil',
    ],

if platform.system() == "Windows":
    import py2exe

    client_install_requires[0].append([
        'pybonjour',
    ])

    modules = ""
    joiner = """
        join.cli = gosa.client.plugins.join.cli:Cli
    """
else:
    client_install_requires[0].append([
        'python_daemon',
        'lockfile',
    ])

    modules = """
        gosa-client.plugins.wakeonlan = gosa.client.plugins.wakeonlan.utils:WakeOnLan
        gosa-client.plugins.notify = gosa.client.plugins.notify.utils:Notify
        gosa-client.plugins.powermanagement = gosa.client.plugins.powermanagement.utils:PowerManagement
        gosa-client.plugins.session = gosa.client.plugins.sessions.main:SessionKeeper
    """
    joiner = """
        join.curses = gosa.client.plugins.join.curses_gui:CursesGUI
        join.cli = gosa.client.plugins.join.cli:Cli
    """

setup(
    name = "gosa.client",
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

    namespace_packages = ['gosa'],

    download_url = "http://oss.gonicus.de/pub/gosa",
    packages = find_packages(exclude=['examples', 'tests']),

    include_package_data = True,
    package_data = {
        'gosa.client': ['data/client.conf'],
    },

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = [
        'nose',
        'NoseXUnit',
        'pylint',
        'babel',
        ],
    install_requires = client_install_requires,
    dependency_links = [
        'http://oss.gonicus.de/pub/gosa/eggs',
        ],

    #TODO: some modules are windows dependent
    entry_points = """
        [console_scripts]
        gosa-client = gosa.client.main:main
        gosa-join = gosa.client.join:main

        [gosa_join.modules]
        %(joiner)s

        [gosa_client.modules]
        gosa-client.command = gosa.client.command:ClientCommandRegistry
        gosa-client.amqp = gosa.client.amqp:AMQPClientHandler
        gosa-client.amqp_service = gosa.client.amqp_service:AMQPClientService
        %(modules)s
    """ % {'modules': modules, 'joiner': joiner},

    console=['gosa/client/gcs.py']
)