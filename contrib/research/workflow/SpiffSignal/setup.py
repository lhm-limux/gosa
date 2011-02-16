from setuptools import setup, find_packages
setup(name             = 'SpiffSignal',
      version          = '0.1.0',
      description      = 'A signal/event mechanism for Python',
      long_description = \
"""
SpiffSignal is a Python module that implements a simple signal/event mechanism.

.. _README file: http://spiff-signal.googlecode.com/svn/trunk/README
""",
      author           = 'Samuel Abels',
      author_email     = 'cheeseshop.python.org@debain.org',
      license          = 'lGPLv2',
      packages         = [p for p in find_packages('src')],
      package_dir      = {'': 'src'},
      requires         = [],
      keywords         = 'spiff signal event mechanism slot trackable',
      url              = 'http://code.google.com/p/spiff-signal/',
      classifiers      = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python',
        'Topic :: Other/Nonlisted Topic',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ])
