#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name = "libinst.preseed",
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
    namespace_package = "libinst",
    packages = find_packages('src', exclude=['examples', 'tests']),
    package_dir={'': 'src'},

    include_package_data = False,

    test_suite = "nose.collector",
    zip_safe = False,

    setup_requires = ['nose', 'NoseXUnit', 'pylint'],
    install_requires = [
        'libinst',
    ],


    entry_points = """
        [libinst.base_methods]
        libinst.preseed = libinst.preseed.methods:DebianPreseed
    """
)
