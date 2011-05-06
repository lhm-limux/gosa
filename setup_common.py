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


common_install_requires = [
    'zope.interface>=3.5',
    'sqlalchemy',
    'babel',
    'pyOpenSSL',
    'lxml',
    'jsonrpc',
    'qpid-python',
    ],

if platform.system() == "Windows":
    common_install_requires[0].append([
        'pybonjour',
    ])
else:
    # Not installable this way:
    # avahi, pygtk (gobject), dbus
    #install_requires[0].append([
    #    'dbus',
    #    'avahi',
    #    'PyGTK',
    #])
    pass

setup(
    name = "gosa.common",
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
        'gosa.common': ['data/stylesheets/*', 'data/events/*'],
    },

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = [
        'nose',
        'NoseXUnit',
        'pylint',
        'babel',
        ],
    install_requires = common_install_requires,
    dependency_links = [
        'http://oss.gonicus.de/pub/gosa/eggs',
        ],

    entry_points = """
        [gosa.modules]
        gosa-agent.amqp = gosa.common.components.amqp:AMQPHandler
    """,
)
