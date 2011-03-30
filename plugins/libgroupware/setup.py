#!/usr/bin/env python
import platform
from setuptools import setup, find_packages

if platform.system() == "Windows":
    modules = """
        [gosa_client.modules]
        gosa-client.exchange = libgroupware.exchange.main:MSExchange
    """
else:
    modules = ""

setup(
    name = "libgroupware",
    version = "1.0",
    author = "Cajus Pollmeier",
    author_email = "pollmeier@gonicus.de",
    description = "Abstraction layer for groupware systems",
    long_description = """
This library tries to unify the management of groupware systems
like Kolab, Exchange and so on.
""",
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
        'Topic :: System :: Monitoring',
    ],

    download_url = "http://oss.gonicus.de/pub/gosa",
    packages = find_packages('.', exclude=['examples', 'tests']),

    include_package_data = True,
    package_data = {
    },

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = ['nose', 'NoseXUnit', 'pylint'],
    #    install_requires = [ 'active_directory' ],

    dependency_links = [
                'http://timgolden.me.uk/python/downloads',
                    ],

    entry_points = """
        [libgroupware.implementations]
        gosa-agent.libgroupware = libgroupware.exchange.manager:ExchangeManager

        %(modules)s

        [gosa.modules]
        gosa-agent.libgroupware = libgroupware.manager:GroupwareManager
    """ % {'modules': modules}
)
