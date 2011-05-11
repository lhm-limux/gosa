#-*- coding: utf-8 -*-
import os
import sys
import codecs
import test_NoseXUnit

import nosexunit.core as ncore
import nosexunit.const as nconst

class TestUnicode(test_NoseXUnit.TestCase):
    
    def test(self):
        # Set up outputs
        stdout = ncore.StdOutRecoder()
        stderr = ncore.StdErrRecorder()
        # Be able to replace outputs
        try:
            # Get a suite
            suite = ncore.XSuite('test_unicode')
            # Starting...
            suite.start()
            stderr.start()
            stdout.start()
            # Add a test
            suite.addTest(ncore.XTest(nconst.TEST_SUCCESS, None))
            # Get UTF-8 output
            sys.stdout.write(u'\xe9')
            sys.stderr.write(u'\xe9')
            # Ending...
            stdout.stop()
            stderr.stop()
            suite.stop()
            suite.setStdout(stdout.content())
            suite.setStderr(stderr.content())
            # Write report
            suite.writeXml(self.target)
        # Finally close outputs
        finally:
            # Close standard one
            stdout.end()
            # Close error one
            stderr.end()
        # Get the output file
        output = os.path.join(self.target, 'TEST-test_unicode.xml')
        # Check if exists
        self.assertExists(output)
        # Get expected value
        expected = u'<system-out><![CDATA[é]]></system-out><system-err><![CDATA[é]]></system-err>'
        # Get generated content
        fd = codecs.open(output, encoding='utf-8')
        found = fd.read()
        fd.close()
        # Check contained
        self.assertTrue(found.find(expected) != -1)

        
if __name__=="__main__":
    test_NoseXUnit.main()
