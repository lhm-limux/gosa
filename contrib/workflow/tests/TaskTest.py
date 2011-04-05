import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

__author__="janw"
__date__ ="$25.05.2010 14:17:55$"

def suite():
    tests = ['testTree']
    return unittest.TestSuite(map(TaskTest, tests))

import MySQLdb
from sqlalchemy                      import *
from sqlalchemy.orm                  import clear_mappers
from SpiffWorkflow                   import Workflow, Task, Job
from SpiffWorkflow.Tasks             import Simple
from SpiffWorkflow.Exception         import WorkflowException
from SpiffWorkflow.Storage           import XmlReader

class TaskTest(unittest.TestCase):
    def setUp(self):
        self.connectDB()
        self.reader = XmlReader()
        self.input = os.path.dirname(__file__) + "/xml/anlage_benutzer.xml"
        self.workflow = self.reader.parse_file(self.input).pop()

    def testFileExists(self):
        assert(os.path.isfile(self.input))
        assert(os.access(self.input, os.R_OK))

    def testReader(self):
        self.reader.parse_file(self.input)
        
    def testTask(self):
        self.reader.parse_file(self.input).pop()

    def testJob(self):
        self.job = Job(self.workflow)
        for name in self.workflow.tasks:
            self.workflow.tasks[name].signal_connect('reached',   self.on_reached_cb)
            self.workflow.tasks[name].signal_connect('completed', self.on_complete_cb)
        while not self.job.is_completed():
            self.job.complete_next()


    def connectDB(self):
        global engine, db

        host = "build-lenny-32.intranet.gonicus.de"
        db_name = "spiff"
        username = "root"
        password = "tester"

        # Connect to MySQL.
        auth        = username + ':' + password
        dbn         = 'mysql://' + auth + '@' + host + '/' + db_name
        engine = create_engine(dbn)
        clear_mappers()

    def on_reached_cb(self, job, task):
        # print "Reached Task: %s" % task.get_name()
        pass

    def on_complete_cb(self, job, task):
        # print "Completed Task: %s" % task.get_name()
        pass

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())