#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name = "libinst",
    version = "1.0",
    author = "Jan Wenzel",
    author_email = "wenzel@gonicus.de",
    description = "Repository and installation abstraction library",
    long_description = """
This library handles the installation, configuration and repositories
for various systems in your setup.
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
        'Topic :: System :: Software Distribution',
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
    install_requires = [
        'zope.interface>=3.5',
        'sqlalchemy',
        'gosa.agent',
        #'python-gnupg',
        'python-debian',
        'pyinotify',
        'GitPython',
        'PyYAML',
    ],
    extra_requires = [
        'python-mysqldb',
    ],


    entry_points = """
        [libinst.repository]
        libinst.debian_handler = libinst.debian.main:DebianHandler

        [libinst.methods]
        libinst.puppet = puppet.methods:PuppetInstallMethod

        [libinst.base_methods]
        #libinst.preseed = preseed.methods:PreseedBaseInstallMethod

        [gosa.modules]
        gosa-agent.libinst = libinst.manage:RepositoryManager

        [gosa_client.modules]
        gosa-client.puppet = puppet.client:PuppetClient

        [puppet.items]
        item.root = puppet.items:PuppetRoot
        item.module = puppet.items:PuppetModule
        item.manifest = puppet.items:PuppetManifest
        item.file = puppet.items:PuppetFile
        item.template = puppet.items:PuppetTemplate
    """
)
