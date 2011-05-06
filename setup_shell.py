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
    name = "gosa.shell",
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

    include_package_data = False,

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = ['nose', 'NoseXUnit', 'pylint', 'babel' ],
    install_requires = ['gosa.common'],

    entry_points = """
        [console_scripts]
        gosa-shell = gosa.shell.main:main
    """,
)
