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


###############################################################################
#                           Build common package                              #
###############################################################################

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
        'gosa.common': ['data/stylsheets/*', 'data/events/*'],
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


###############################################################################
#                           Build agent package                               #
###############################################################################

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

    namespace_packages = ['gosa'],

    download_url = "http://oss.gonicus.de/pub/gosa",
    packages = find_packages(exclude=['examples', 'tests']),

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


###############################################################################
#                           Build client package                              #
###############################################################################

client_install_requires = [
    'gosa.common',
    'netaddr',
    'netifaces',
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
        gosa-client.plugins.powermanagement = gosa.client.plugins.powermanagement.utils:PowerManagement
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


###############################################################################
#                             Build dbus package                              #
###############################################################################

setup(
    name = "gosa.dbus",
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

    test_suite = "nose.collector",

    setup_requires = [
        'nose',
        'NoseXUnit',
        'pylint',
        'babel',
        ],
    install_requires = [
        'gosa.common',
        ],
    dependency_links = [
        'http://oss.gonicus.de/pub/gosa/eggs',
        ],

    #TODO: some modules are windows dependent
    entry_points = """
        [console_scripts]
        gosa-dbus = gosa.dbus.main:main

        [gosa_dbus.modules]
        gosa-dbus.shell = gosa.dbus.plugins.shell.main:DBusShellHandler
        gosa-dbus.notify = gosa.dbus.plugins.notify.main:DBusNotifyHandler
        gosa-dbus.puppet = gosa.dbus.plugins.puppet.main:PuppetDBusHandler
    """,
)


###############################################################################
#                            Build shell package                              #
###############################################################################

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

    include_package_data = True,

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = ['nose', 'NoseXUnit', 'pylint', 'babel' ],
    install_requires = ['gosa.common'],

    entry_points = """
        [console_scripts]
        gosa-shell = gosa.shell.main:main
    """,
)
