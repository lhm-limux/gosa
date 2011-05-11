#-*- coding: utf-8 -*-
import os
import imp
import sys
import shutil
import logging
import unittest
import ConfigParser

import nose.plugins

import nosexunit.const
import nosexunit.plugin

# Absolute folder of this file
FOLDER = os.path.dirname(os.path.abspath(__file__))

# Model configuration file
CFG_TST_MODEL = 'test.properties.model'
# User configuration file
CFG_TST_USER = 'test.properties'

# Get a logger
logger = logging.getLogger(__name__)
# Set level
logger.setLevel(logging.INFO)
# Create the handler
console = logging.StreamHandler(sys.stdout)
# Add handler
logger.addHandler(console)

class TestError(StandardError):
    '''Exception class for tests'''
    pass

class TestCase(unittest.TestCase):
    '''Super class of test for NoseXUnit basic tests'''

    def setUp(self):
        '''Set up for NoseXUnit super class of test'''
        # Call the super class
        unittest.TestCase.setUp(self)
        # Get the folder containing the test file
        self.folder = os.path.dirname(get_class_path(self))
        # Test properties
        self.i_properties = parse_properties([FOLDER, self.folder, ])
        # Get the target folder
        self.work = os.path.abspath(os.getenv('NOSEXUNIT_WORK', os.path.expandvars(self.get('work'))))
        # Get the source folder
        self.source = os.path.join(self.work, 'source')
        # get the report folder
        self.target = os.path.join(self.work, 'target')
        # Check if debug
        self.i_debug = int(self.get('debug'))
        # Set up the target folder
        self.setUpTarget()

    def setUpTarget(self):
        '''Create the target tree'''
        # Cleanup before
        self.tearDownTarget(force=True)
        # Create the folders
        for folder in [self.source, self.target, ]:
            # Check if not exists and create it
            if not os.path.exists(folder): os.makedirs(folder)

    def tearDown(self):
        '''Tear down for NoseXUnit super class of test'''
        # Clean the environment
        self.tearDownTarget()
        # Call super class
        unittest.TestCase.tearDown(self)

    def tearDownTarget(self, force=False):
        '''Delete the target tree'''
        # Check if folder exists
        if os.path.isdir(self.work) and (not self.i_debug or force):
            # Display if fails
            def onerror(*args): sys.stderr.write('fail to delete %s\n' % args[1])
            # Drop the folder
            shutil.rmtree(self.work, onerror=onerror)

    def get(self, entry):
        '''Get the provided property'''
        # Check if exists
        if not self.i_properties.has_key(entry):
            # Not available, raise
            raise TestError('no such property in the current configuration: %s' % entry)
        # Return the value of the property
        return self.i_properties[entry]

    def has(self, entry):
        '''Return True if has the entry in the configuration'''
        # Try to get it
        try: self.get(entry)
        # Not available
        except: return False
        # Got it
        return True

    def getworkfile(self, content):
        '''Create a file with provided content'''
        # Get the work path
        path = self.getworkpath()
        # Open the file
        fd = open(path, 'w')
        # Write the content
        fd.write(content)
        # Close the file
        fd.close()
        # Return the path of the created file
        return path
    
    def getworkpath(self):
        '''Get the path of a work file'''
        # File counter
        count = 0
        # While file path not found, increment
        while True:
            # Get the potential path
            path = os.path.join(self.work, 'work_%d' % count)
            # Check if exists
            if not os.path.exists(path): return path
            # If already exists, loop
            count += 1
    
    def assertNone(self, value):
        '''Assert that value is None'''
        self.assertEquals(None, value)
        
    def assertNotNone(self, value):
        '''Assert that value is not None'''
        self.assertNotEquals(None, value)

    def assertExists(self, path):
        '''Assert that the provided path exists'''
        self.assertTrue(os.path.exists(path))

    def assertSet(self, expected, found):
        '''Assert that list match without order'''
        # Check length
        self.assertEquals(len(expected), len(found))
        # Go threw the elements to check the number
        for exp in expected: self.assertEquals(expected.count(exp), found.count(exp))

    def assertRaiseOutput(self, excClass, output, callableObj, *args, **kwargs):
        '''Assert on exception and its message'''
        # Call function which is supposed to raise
        try: callableObj(*args, **kwargs)
        # Get the error and check the message
        except excClass, e: self.assertEquals(output, str(e))
        # Not raised, this is an error
        else:
            # Get the exception's name
            if hasattr(excClass,'__name__'): excName = excClass.__name__
            else: excName = str(excClass)
            # Raise the failure
            raise self.failureException, '%s not raised' % excName

    def assertContent(self, expected, path):
        '''Assert on content in the file'''
        # Open the file
        fd = open(path, 'r')
        # read its content
        found = fd.read()
        # Close the file
        fd.close()
        # Assert on file content
        self.assertEquals(expected, found)

class PluginTestCase(nose.plugins.PluginTester, TestCase):
    '''Super class of test for NoseXUnit plug in tests'''

    activate = '--with-nosexunit'

    OPT_CORE_TARGET = '--core-target'

    OPT_CORE_SOURCE = '--source-folder'

    OPT_CORE_SEARCH_SOURCE = '--search-source'
    
    OPT_CORE_SEARCH_TEST = '--search-test'
    
    OPT_EXTRA_INCLUDE = '--extra-include'

    OPT_EXTRA_EXCLUDE = '--extra-exclude'

    OPT_EXTRA_TEST_PROCESS = '--extra-test-process'

    OPT_AUDIT_ENABLE = '--enable-audit'
    
    OPT_AUDIT_TARGET = '--audit-target'
    
    OPT_AUDIT_OUTPUT = '--audit-output'
    
    OPT_AUDIT_CONFIG = '--audit-config'

    OPT_COVER_ENABLE = '--enable-cover'
    
    OPT_COVER_TARGET = '--cover-target'
    
    OPT_COVER_CLEAN = '--cover-clean'

    OPT_COVER_COLLECT = '--cover-collect'

    def setUp(self):
        '''Set up for plug in tests'''
        # Call test set up
        TestCase.setUp(self)
        # Create the plug in
        self.plugins = [nose.plugins.deprecated.Deprecated(), nose.plugins.skip.Skip(), nosexunit.plugin.NoseXUnit(), ]
        # Reset the suite path
        self.suitepath = None
        # Reset the line
        self.args = []
        # Set the core target
        self.core_target = os.path.join(self.target, 'core')
        # Set the audit target
        self.audit_target = os.path.join(self.target, 'audit')
        # Set the cover target
        self.cover_target = os.path.join(self.target, 'cover')
        # Set up the test case
        self.setUpCase()
        # Call plug in set up
        nose.plugins.PluginTester.setUp(self)
    
    def setUpCase(self):
        '''Used instead of setUp in test cases'''
        pass
    
    def add(self, opt, value=None):
        '''Add an option to the line'''
        # Check if single option
        if value is None: self.args.append(opt)
        # Else this is an option with value
        else: self.args.append('%s=%s' % (opt, value))
        
    def setUpCore(self, tg=None, src=None, s_src=False, s_tst=False, e_inc=[], e_exc=None, e_tst=False):
        '''Set up the core'''
        # Set target is asked
        if tg: self.add(self.OPT_CORE_TARGET, tg) 
        # Add source if asked
        if src: self.add(self.OPT_CORE_SOURCE, src)
        # Check if search source
        if s_src: self.add(self.OPT_CORE_SEARCH_SOURCE)
        # Check is search tests
        if s_tst: self.add(self.OPT_CORE_SEARCH_TEST)

    def setUpExtra(self, includes=[], excludes=nosexunit.const.AUDIT_COVER_EXCLUDE, tp=False):
        '''Set up extra configuration'''
        # Go threw the included packages
        for include in includes: self.add(self.OPT_EXTRA_INCLUDE, include)
        # Go threw the excluded packages
        for exclude in excludes: self.add(self.OPT_EXTRA_EXCLUDE, exclude)
        # Set test processing flag
        if tp: self.add(self.OPT_EXTRA_TEST_PROCESS)
    
    def setUpAudit(self, tg=None, out=None, conf=None):
        '''Set up audit'''
        # Enable
        self.add(self.OPT_AUDIT_ENABLE)
        # Set target is asked
        if tg: self.add(self.OPT_AUDIT_TARGET, tg)
        # Set  output
        if out: self.add(self.OPT_AUDIT_OUTPUT, out)
        # Set configuration
        if conf: self.add(self.OPT_AUDIT_CONFIG, conf)

    def setUpCover(self, tg=None, clean=False, collect=False):
        '''Set up audit'''
        # Enable
        self.add(self.OPT_COVER_ENABLE)
        # Set target is asked
        if tg: self.add(self.OPT_COVER_TARGET, tg)
        # Check if clean results
        if clean: self.add(self.OPT_COVER_CLEAN)
        # Check if has to collect
        if collect: self.add(self.OPT_COVER_COLLECT)
        # Get coverage package
        import coverage
        # Clean coverage
        coverage.the_coverage = None
        # Create a new one
        coverage.the_coverage = coverage.coverage()
        # Set the location
        coverage.cache_location = os.path.join(self.cover_target, 'cover.')

    def wasSuccessful(self):
        return self.nose.success
    
    def assertWasSuccessful(self):
        self.assertTrue(self.wasSuccessful())
        
    def assertWasNotSuccessful(self):
        self.assertFalse(self.wasSuccessful())

class FS(object):
    '''Represent a file system object'''
    
    def __init__(self, desc):
        '''Initialize the file system object'''
        # Store the description
        self.i_desc = desc
        # Store the parent package
        self.i_father = None
        # Store the path
        self.i_path = None
        
    def desc(self):
        '''Get the description of the package'''
        return self.i_desc
    
    def father(self):
        '''Get the parent package'''
        return self.i_father

    def save(self, folder):
        '''Save the object'''
        raise TestError('method save not implemented')
    
    def path(self):
        '''Return the path'''
        # Check if initialized
        if self.i_path is None: raise TestError('path can be called only after save')
        # Get the path
        return self.i_path
    
    def append(self, fs):
        '''Append a FS to this object'''
        # Add to the list
        list.append(self, fs)
        # Add father to children
        fs.i_father = self    

class FSContent(FS):
    '''Represent a file system object that has content'''
    
    def __init__(self, desc, content=''):
        '''Initialize the file system object with content'''
        # Call super
        FS.__init__(self, desc)
        # Store the content
        self.i_content = content
        
    def content(self):
        '''Return the content'''
        return self.i_content
        
class Folder(FS, list):
    '''Represent a folder'''
    
    def __init__(self, desc):
        '''Initialize the folder'''
        # Call super
        FS.__init__(self, desc)
        # Call super
        list.__init__(self)
    
    def save(self, folder):
        '''Create the folder'''
        # Get the folder path
        self.i_path = os.path.join(folder, self.i_desc)
        # Create the folder
        os.makedirs(self.i_path)
        # Go threw the children
        for child in self: child.save(self.i_path)
        # Return the object
        return self
    
class File(FSContent):
    '''Represent a file'''

    def save(self, folder):
        '''Save the file in the provided folder'''
        # Store the path
        self.i_path = os.path.join(folder, self.i_desc)
        # Create the file
        fd = open(self.i_path, 'w')
        # Set the content
        fd.write(self.i_content)
        # Close the file
        fd.close()

class Source(FSContent):
    '''Represent a source file'''
    
    def full(self):
        '''Full package description'''
        # Check if there is a parent package
        if self.i_father is None: return self.i_desc
        # There is actually a parent package
        else: return '%s.%s' % (self.father().full(), self.i_desc)

class Package(Source, list):
    '''Represent a package'''

    def __init__(self, desc, content=''):
        '''Initialize the package'''
        # Call super
        Source.__init__(self, desc, content)
        # Call super
        list.__init__(self)

    def save(self, folder):
        '''Create the package in the provided folder'''
        # Get the folder
        self.i_path = os.path.join(folder, self.i_desc)
        # Create the folder
        os.makedirs(self.i_path)
        # Create the __init__
        ini = open(os.path.join(self.i_path, '__init__.py'), 'w')
        # Set the content
        ini.write(self.i_content)
        # Close the file
        ini.close()
        # Go threw the children
        for child in self: child.save(self.i_path)
        # Return the object
        return self

class Module(Source):
    '''Represent a module'''    

    def save(self, folder):
        '''Create the module in the folder'''
        # Store the path
        self.i_path = os.path.join(folder, '%s.py' % self.i_desc)
        # Create the file
        fd = open(self.i_path, 'w')
        # Set the content
        fd.write(self.i_content)
        # Close the file
        fd.close()
        # Return the object
        return self

class TestModule(Module):
    '''Represent a test module'''
    
    def __init__(self, desc, cls):
        '''Initialize the file system object with content'''
        # Store the class description
        self.i_cls = cls
        # Get the content
        text = """
import nose
import unittest
class %s(unittest.TestCase):
    pass
""" % self.i_cls
        # Call super
        Module.__init__(self, desc, text)
        
    def cls(self):
        '''Get the class description'''
        return self.i_cls

    def addError(self, fct):
        '''Add an error test'''
        self.i_content = """%s
    def %s(self): raise StandardError('this is an error')
""" % (self.i_content, fct)
    
    def addSuccess(self, fct):
        '''Add a successful test'''
        self.i_content = """%s
    def %s(self): pass
""" % (self.i_content, fct)

    def addFailure(self, fct):
        '''Add a failing test'''
        self.i_content = """%s
    def %s(self): self.fail('this is a failure')
""" % (self.i_content, fct)

    def addSkip(self, fct):
        '''Add a skipped test'''
        self.i_content = """%s
    def %s(self): raise nose.SkipTest()
""" % (self.i_content, fct)

    def addDeprecated(self, fct):
        '''Add a deprecated test'''
        self.i_content = """%s
    def %s(self): raise nose.DeprecatedTest()
""" % (self.i_content, fct)

    def addCustom(self, fct, content):
        self.i_content = """%s
    def %s(self):
        %s
""" % (self.i_content, fct, '\n        '.join(content.split('\n')))

def parse_properties(folders):
    '''Return the parsed properties'''
    # List of the properties
    properties = {}
    # Go threw the given folders
    for folder in folders:
        # Go threw the configuration files
        for fn in [ os.path.join(folder, CFG_TST_MODEL), os.path.join(folder, CFG_TST_USER), ]:
            # Check if the file exists
            if os.path.isfile(fn):
                # Create a parser
                parser = ConfigParser.ConfigParser()
                # Read the configuration
                parser.read(fn)
                # Get the properties
                for section in parser.sections():
                    # Get the section
                    for option in parser.options(section):
                        # Get the option
                        properties[option.lower()] = parser.get(section, option)
    # Return the properties
    return properties

def get_class_path(cls):
    '''Given an instance of a class, return his definition path'''
    # Get the head module
    mod = __import__(cls.__module__)
    # Get the new module name
    mods = cls.__module__.split('.')
    # Set the new name
    mods[0] = 'mod'
    # Get the path
    return os.path.abspath(eval('%s.__file__' % '.'.join(mods)))

def main():
    '''Call main method of test'''
    unittest.main()
    
if __name__=="__main__":
    main()

    