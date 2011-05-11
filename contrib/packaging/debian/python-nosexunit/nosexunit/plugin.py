#-*- coding: utf-8 -*-
import os
import re
import sys
import time
import logging

import nose
import nose.util

from nose.plugins import Plugin

import nosexunit.core as ncore
import nosexunit.audit as naudit
import nosexunit.cover as ncover
import nosexunit.const as nconst
import nosexunit.tools as ntools
import nosexunit.excepts as nexcepts

# Get a logger
logger =  logging.getLogger('%s.%s' % (nconst.LOGGER, __name__))

class NoseXUnit(Plugin, object):

    def help(self):
        '''Help'''
        return 'Output XML report of test status'

    def options(self, parser, env=os.environ):
        '''Add launch options for NoseXUnit'''
        # Call super
        Plugin.options(self, parser, env)
        # ---------------------------------------------------------------------
        # CORE
        # ---------------------------------------------------------------------
        # Add test target folder
        parser.add_option('--core-target',
                          action='store',
                          default = nconst.TARGET_CORE,
                          dest='core_target',
                          help='Output folder for test reports (default is %s).' % nconst.TARGET_CORE)
        # Add source folder
        parser.add_option('--source-folder',
                          action='store',
                          default=None,
                          dest='source',
                          help='Set source folder (optional for core functionality, required for audit and coverage). Add folder in sys.path.')
        # Search sources in source tree
        parser.add_option('--search-source',
                          action='store_true',
                          default=False,
                          dest='search_source',
                          help="Walk in the source folder to add deeper folders in sys.path if they don't contain __init__.py file. Works only if --source-folder is defined.")
        # Search tests in 
        parser.add_option('--search-test',
                          action='store_true',
                          default=False,
                          dest='search_test',
                          help='Search tests in folders with no __init__.py file (default: do nothing).')
        # Package to process in audit or coverage extensions
        parser.add_option('--extra-include',
                          action='append',
                          default=[],
                          dest='extra_includes',
                          help='Include packages for audit or coverage processing (default: take all packages in --source-folder, except those defined in --extra-exclude). Package name specified with regex.')
        # Package to do not process in audit or coverage extensions
        parser.add_option('--extra-exclude',
                          action='append',
                          default=nconst.AUDIT_COVER_EXCLUDE,
                          dest='extra_excludes',
                          help='Exclude packages for audit or coverage processing (default: %s). Useless if --extra-include defined. Package name specified with regex.' % (', '.join(nconst.AUDIT_COVER_EXCLUDE), ))
        # Package to do not process in audit or coverage extensions
        parser.add_option('--extra-test-process',
                          action='store_true',
                          default=False,
                          dest='extra_test_process',
                          help='Include packages matching the test pattern in audit or coverage processing (default: no).')
        # ---------------------------------------------------------------------
        # AUDIT
        # ---------------------------------------------------------------------
        # Add option to enable audit
        parser.add_option('--enable-audit',
                          action='store_true',
                          default=False,
                          dest='audit',
                          help='Use PyLint to audit source code (default: no)')        
        # Add PyLint target folder
        parser.add_option('--audit-target',
                          action='store',
                          default=nconst.TARGET_AUDIT,
                          dest='audit_target',
                          help='Output folder for PyLint reports (default is %s).' % nconst.TARGET_AUDIT)
        # Add PyLint output
        parser.add_option('--audit-output',
                          action='store',
                          default=nconst.AUDIT_DEFAULT_REPORTER,
                          dest='audit_output',
                          help='Output for audit reports: %s (default: %s).' % (', '.join(naudit.outputs()), nconst.AUDIT_DEFAULT_REPORTER))
        # Add PyLint configuration file
        parser.add_option('--audit-config',
                          action='store',
                          default=None,
                          dest='audit_config',
                          help='Configuration file for PyLint (optional).')
        # ---------------------------------------------------------------------
        # COVER
        # ---------------------------------------------------------------------
        # Add option to enable coverage
        parser.add_option('--enable-cover',
                          action='store_true',
                          default=False,
                          dest='cover',
                          help='Use coverage to audit source code (default: no)')        
        # Add coverage target folder
        parser.add_option('--cover-target',
                          action='store',
                          default = nconst.TARGET_COVER,
                          dest='cover_target',
                          help='Output folder for coverage reports (default is %s).' % nconst.TARGET_COVER)
        # Check if clean folder
        parser.add_option('--cover-clean',
                          action='store_true',
                          default=False,
                          dest='cover_clean',
                          help='Clean previous coverage results (default: no).')
        # Collect extra coverage files in target folder
        parser.add_option('--cover-collect',
                          action='store_true',
                          default=False,
                          dest='cover_collect',
                          help='Collect other coverage files potentially generated in cover target folder. These extra files should have the following pattern: %s.* (default: no).' % nconst.COVER_OUTPUT_BASE)
    
    def configure(self, options, config):
        '''Configure the plug in'''
        # Call super
        Plugin.configure(self, options, config)
        # ---------------------------------------------------------------------
        # NOSE
        # ---------------------------------------------------------------------
        # Store the configuration
        self.config = config
        # Check if processes enabled
        try: self.fork = 1 != max(int(options.multiprocess_workers), 1)
        # If multiprocess not available
        except: self.fork = False
        # ---------------------------------------------------------------------
        # CORE
        # ---------------------------------------------------------------------
        # Store test target folder
        self.core_target = os.path.abspath(options.core_target)
        # Store source folder
        if options.source: self.source = os.path.abspath(options.source)
        else: self.source = None
        # Check if has to search sources
        self.search_source = options.search_source
        # Check if has to search tests
        self.search_test = options.search_test
        # Store included packages
        self.extra_includes = [ re.compile(extra_include) for extra_include in nose.util.tolist(options.extra_includes) ]
        # Store excluded packages
        self.extra_excludes = [ re.compile(extra_exclude) for extra_exclude in nose.util.tolist(options.extra_excludes) ]
        # Store if process packages with test pattern
        self.extra_test_process = options.extra_test_process
        # ---------------------------------------------------------------------
        # AUDIT
        # ---------------------------------------------------------------------
        # Check if enable audit
        self.audit = options.audit
        # Check if audit asked
        if self.audit:
            # Check if available
            available, error = naudit.available()
            # Check if available
            if not available:
                # Raise
                raise nexcepts.PluginError('audit not available in NoseXUnit, error while loading dependences: %s' % error)
            # Store PyLint target folder
            self.audit_target = os.path.abspath(options.audit_target)
            # Store PyLint configuration file
            if options.audit_config: self.audit_config = os.path.abspath(options.audit_config)
            else: self.audit_config = None
            # Get the output
            self.audit_output = options.audit_output.lower()
        # ---------------------------------------------------------------------
        # COVER
        # ---------------------------------------------------------------------
        # Check if coverage is enabled
        self.cover = options.cover
        # Check if audit asked
        if self.cover:
            # Check if available
            available, error = ncover.available()
            # Check if available
            if not available:
                # Raise
                raise nexcepts.PluginError('coverage not available in NoseXUnit, error while loading dependences: %s' % error)
            # Check if no worker test runners
            if self.fork:
                # Raise
                raise nexcepts.PluginError('coverage not available with --processes option')
            # Check if clean folder
            self.cover_clean = options.cover_clean
            # Check if collect
            self.cover_collect = options.cover_collect
            # Store coverage target folder
            self.cover_target = os.path.abspath(options.cover_target)
    
    def initialize(self):
        '''Set the environment'''
        # Check that source folder exists if specified
        if self.source and not os.path.isdir(self.source):
            # Source folder doesn't exist
            raise nexcepts.NoseXUnitError("source folder doesn't exist: %s" % self.source)
        # Create the core target folder
        ntools.create(self.core_target)
        # Clean the target folder of the core
        ntools.clean(self.core_target, nconst.PREFIX_CORE, nconst.EXT_CORE)
        # Initialize the packages
        self.packages = {}
        # Add the source folder in the path
        if self.source:
            # Get the packages
            self.packages = ntools.packages(self.source, search=self.search_source)
            # Get the folders to add in the path
            folders = []
            # Go threw the packages
            for package in self.packages.keys():
                # Check if is as sub package or a sub module
                if package.find('.') == -1:
                    # Get the folder
                    folder = os.path.dirname(self.packages[package])
                    # If not already in, add it
                    if folder not in folders: folders.append(folder)
            # Get current path
            backup = sys.path
            # Clean up
            sys.path = []
            # Add to the path
            for folder in folders:
                # Log
                logger.info('add folder in sys.path: %s' % folder)
                # Add to the path
                sys.path.append(folder)
            # Add old ones
            sys.path.extend(backup)
        # Check if audit enabled
        if self.audit:
            # Check if source folder specified
            if not self.source: raise nexcepts.NoseXUnitError('source folder required for audit')
            # Check output
            if self.audit_output not in naudit.outputs(): raise nexcepts.NoseXUnitError('output not available for audit: %s' % self.audit_output)
            # Create the target folder for audit
            ntools.create(self.audit_target)
            # Get the package list for audit
            self.audit_packages = [ package for package in self.packages.keys() if package.find('.') == -1 and self.enable(package) ]
            # Check at least one
            if self.audit_packages == []: raise nexcepts.NoseXUnitError('no package to audit')
            # Start audit
            self.audit_cls = naudit.audit(self.source, self.audit_packages, self.audit_output, self.audit_target, self.audit_config)
        # No test class
        else: self.audit_cls = []
        # Check if coverage enabled
        if self.cover:
            # Check if source folder specified
            if not self.source: raise nexcepts.NoseXUnitError('source folder required for coverage')
            # Create the target folder for audit
            ntools.create(self.cover_target)
            # Get the skipped ones
            self.skipped = sys.modules.keys()[:]
            # Get the coverage packages
            self.cover_packages = [ package for package in self.packages.keys() if self.enable(package) ]
            # Check at least one
            if self.cover_packages == []: raise nexcepts.NoseXUnitError('no package to cover')
            # Start coverage
            ncover.start(self.cover_clean, self.cover_packages, self.cover_target)

    def enable(self, package):
        '''Check if a package has to be processed'''
        # Check if is a test
        if self.conf.testMatch.search(package) and not self.extra_test_process: return False
        # Check if include list defined
        if self.extra_includes != []: return self.packageMatch(package, self.extra_includes)
        # Check exclusions
        else: return not self.packageMatch(package, self.extra_excludes)

    def packageMatch(self, package, patterns):
        '''Go threw the patterns to check if package match'''
        # Go threw the patterns
        for p in patterns:
            # Check if match
            if p.match(package):
                # Yes!
                return True
        # Failed to match
        return False

    def prepareTest(self, test):
        '''Add the generated tests'''
        # Add the audit tests
        for audit_test in self.audit_tests: test.addTest(audit_test)

    def prepareTestLoader(self, loader):
        '''Load the generated tests'''
        # Load the audit tests
        self.audit_tests = [ loader.loadTestsFromTestCase(cls) for cls in self.audit_cls ]

    def begin(self):
        '''Initialize the plug in'''
        # Initialize plug in
        self.initialize()
        # Store the module
        self.module = None
        # Store the suite
        self.suite = None
        # Store the start time
        self.start = None
        # Get a STDOUT recorder
        self.stdout = ncore.StdOutRecoder()
        # Get a STDERR recorder
        self.stderr = ncore.StdErrRecorder()

    def wantDirectory(self, dirname):
        '''Check if search tests in this folder'''
        # Check if search test option enable and if there is no __init__ in the folder
        if self.search_test and not os.path.exists(os.path.join(dirname, nconst.INIT)): return True
        # Else I don't care
        else: return

    def enableSuite(self, test):
        '''Check that suite exists. If not exists, create a new one'''
        # Get the current module
        current = ntools.get_test_id(test).split('.')[0]
        # Check if this is a new one
        if self.module != current:
            # Set the new module
            self.module = current
            # Stop the previous suite
            self.stopSuite()
            # Start a new one
            self.startSuite(self.module)

    def startSuite(self, module):
        '''Start a new suite'''
        # Create a suite
        self.suite = ncore.XSuite(module)
        # Start it
        self.suite.start()
        # Clean STDOUT
        self.stderr.reset()
        # Clean STDERR
        self.stdout.reset()
        # Start recording STDOUT
        self.stderr.start()
        # Start recording STDERR
        self.stdout.start()
   
    def startTest(self, test):
        '''Record starting time'''
        # Enable suite
        self.enableSuite(test)
        # Get the start time
        self.start = time.time()

    def addTestCase(self, kind, test, err=None):
        '''Add a new test result in the current suite'''
        # Create a test
        elmt = ncore.XTest(kind, test, err=err)
        # Set the start time
        elmt.setStart(self.start)
        # Set the stop time
        elmt.stop()
        # Enable the suite
        self.enableSuite(test)
        # Add test to the suite
        self.suite.addTest(elmt)

    def addError(self, test, err):
        '''Add a error test'''
        # Get the king of error
        kind = nconst.TEST_ERROR
        # Check if skipped
        if isinstance(test, nose.SkipTest): kind = nconst.TEST_SKIP
        # Check if useless
        elif isinstance(test, nose.DeprecatedTest): kind = nconst.TEST_DEPRECATED
        # Add the test
        self.addTestCase(kind, test, err=err)

    def addFailure(self, test, err):
        '''Add a failure test'''
        self.addTestCase(nconst.TEST_FAIL, test, err=err)

    def addSuccess(self, test):
        '''Add a successful test'''
        self.addTestCase(nconst.TEST_SUCCESS, test)

    def stopSuite(self):
        '''Stop the current suite'''
        # Check if a suite exists
        if self.suite != None:
            # Stop recording on STDOUT
            self.stdout.stop()
            # Stop recording on STDERR
            self.stderr.stop()
            # Stop the suite
            self.suite.stop()
            # Affect recorded STDOUT to the suite
            self.suite.setStdout(self.stdout.content())
            # Affect recorded STDERR to the suite
            self.suite.setStderr(self.stderr.content())
            # Create XML
            self.suite.writeXml(self.core_target)
            # Clean the suite
            self.suite = None

    def report(self, stream):
        '''Create the report'''
        # Check if coverage enabled
        if self.cover:
            # Get the package to cover
            entries = [ package for entry, package in sys.modules.items() if self.consider(entry, package) ]
            # Stop coverage
            ncover.stop(stream, entries, self.cover_target, self.cover_collect)

    def consider(self, entry, package):
        '''Check if the package as to be covered'''
        # Check if skipped
        if entry in self.skipped: return False
        # Check if has a __file__ attribute
        if not hasattr(package, '__file__'): return False
        # Get the path
        path = nose.util.src(package.__file__)
        # Check path
        if not path or not path.endswith('.py'): return False
        # Go threw the packages
        if entry in self.cover_packages: return True
        # Exclude by default
        return False

    def finalize(self, result):
        '''Set the old standard outputs'''
        # Stop the current suite
        self.stopSuite()
        # Clean STDOUT recorder
        self.stderr.end()
        # Clean STDERR recorder
        self.stdout.end()
        # Check if fork
        if self.fork:
            # Results not directly collected, available only there
            fork_suite = ncore.XSuite('multiprocess')
            # Create a fake id for successful tests
            class FakeTest(object):
                # Store unique success ID
                def __init__(self, pos): self.pos = pos
                # Add ID function
                def id(self): return 'nose.multiprocess.success%d' % self.pos
            # Add success
            for i in range(result.testsRun): fork_suite.addTest(ncore.XTest(nconst.TEST_SUCCESS, FakeTest(i)))
            # Add errors
            for test, err in result.errors: fork_suite.addTest(ncore.XTest(nconst.TEST_ERROR, test, err=err))
            # Add failures
            for test, err in result.failures: fork_suite.addTest(ncore.XTest(nconst.TEST_FAIL, test, err=err)) 
            # Write
            fork_suite.writeXml(self.core_target)
