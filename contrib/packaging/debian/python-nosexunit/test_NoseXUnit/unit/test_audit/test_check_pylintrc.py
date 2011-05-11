#-*- coding: utf-8 -*-
import os
import test_NoseXUnit

import nosexunit.audit as naudit
import nosexunit.excepts as nexcepts

class TestCheckPyLintRc(test_NoseXUnit.TestCase):
    
    def assertPyLintRc(self, section, option):
        '''Assert that raises when in PyLint configuration'''
        content = """[%s]
%s = foo
""" % (section, option)
        path = self.getworkfile(content)
        self.assertRaises(nexcepts.AuditError, naudit.check_pylintrc, path)
    
    def test_reports_output_format(self):
        self.assertPyLintRc('REPORTS', 'output-format')

    def test_reports_include_ids(self):
        self.assertPyLintRc('REPORTS', 'include-ids')

    def test_reports_files_output(self):
        self.assertPyLintRc('REPORTS', 'files-output')

    def test_reports_reports(self):
        self.assertPyLintRc('REPORTS', 'reports')

    def test_reports_rcfile(self):
        self.assertPyLintRc('MASTER', 'rcfile')


if __name__=="__main__":
    test_NoseXUnit.main()