#-*- coding: utf-8 -*-
import sys
import distutils.util

if sys.version_info[0] > 2 or (sys.version_info[0] == 2 and sys.version_info[1] >= 5):
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup
else:
    import warnings
    warnings.warn('setuptools not used')
    from distutils.core import setup

execfile(distutils.util.convert_path('nosexunit/__init__.py'))

setup(
    name = "NoseXUnit",
    version = __version__,
    description = "XML Output plugin for Nose",
    long_description = "A plugin for nose/nosetests that produces an XML report of the result of a test.",
    author = "Olivier Mansion",
    author_email = "nosexunit@gmail.com",
    zip_safe = True,
    license = "GNU Library or Lesser General Public License (LGPL)",
    url = "http://nosexunit.sourceforge.net",
    packages = ['nosexunit',
                'nosexunit.cover',
                'nosexunit.audit', ],
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing',
        ],
    install_requires = ['nose >= 0.11.1',
                        'pylint >= 0.18.1',
                        'coverage == 2.85', 
                        'kid >= 0.9.6',
                        'pygments >= 1.0', ],
    package_data = {'nosexunit': ['nosexunit.css',
                                  'nosexunit.js',
                                  'blank.png', ],
                    'nosexunit.audit': ['abstract.html',
                                        'code.html',
                                        'detail.html',
                                        'index.html',
                                        'listing.html',
                                        'error.html', ],
                    'nosexunit.cover': ['abstract.html',
                                        'code.html',
                                        'index.html',
                                        'listing.html',
                                        'error.html',
                                        'cobertura.xml',
                                        'clover.xml', ], },
    entry_points = {'nose.plugins.0.10': [ 'nosexunit = nosexunit.plugin:NoseXUnit' ], },
    test_suite = 'nose.collector',
)

