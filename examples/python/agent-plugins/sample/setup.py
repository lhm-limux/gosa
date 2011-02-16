#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name = "sample",
    version = "0.1",
    author = "{AUTHOR}",
    author_email = "{MAIL}",
    description = "{DESCRIPTION}",
    long_description = """
{LONG_DESCRIPTION}
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
        'gosa.agent',
    ],
    extra_requires = [
    ],


    entry_points = """
        [gosa.modules]
        sample.module = sample.module:SampleModule
    """
)
