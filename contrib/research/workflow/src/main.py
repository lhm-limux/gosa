#!/usr/bin/env python

import os.path
import MySQLdb
from sqlalchemy                      import *
from sqlalchemy.orm                  import clear_mappers

__author__="janw"
__date__ ="$21.05.2010 16:55:13$"

from SpiffWorkflow.Storage import XmlReader
from SpiffWorkflow.Server import *
from SpiffWorkflow import Job, Workflow, Task

import pickle, pprint

data_file = os.path.dirname(__file__) + "/job.pk"
workflow_file = os.path.dirname(__file__) + "/../tests/xml/anlage_benutzer.xml"

def connectDB():
    global engine, db, driver

    host = "build-lenny-32.intranet.gonicus.de"
    db_name = "spiff"
    username = "root"
    password = "tester"

    # Connect to MySQL.
    auth        = username + ':' + password
    dbn         = 'mysql://' + auth + '@' + host + '/' + db_name
    engine = create_engine(dbn)
    clear_mappers()
    driver = Driver(engine)

def getJob():
    global data_file, workflow_file
    reader = XmlReader()
    workflow = reader.parse_file(workflow_file).pop()
    if os.access(data_file, os.R_OK):
        input = open(data_file, 'rb')
        job   = pickle.load(input)
        input.close()
        os.remove(data_file)
    else:
        job = Job(workflow)
    return job

def setJob(job):
    global data_file
    result = False
    if not isinstance(job, Job):
        return result
    if os.access(os.path.dirname(data_file), os.W_OK):
        output = open(data_file, 'wb')
        pickle.dump(job, output, -1)
        output.close()
        result = True
    else:
        print "Datafile not accessible"
    return result

def main():
    #connectDB()
    job = getJob()
    job.complete_next()
    if setJob(job):
        print "Job has been saved successfully"
    else:
        print "Problem saving job"

if __name__ == "__main__":
    main()