#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import sys
import inspect
from time import sleep
from gosa.common.components.scheduler import Scheduler, set_job_property
from gosa.common.components.scheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore
from datetime import datetime, timedelta

#logging.basicConfig(level=logging.DEBUG)
#console = logging.StreamHandler()
#logging.getLogger('').addHandler(console)


def test1(text):
    print "-> test1(%s)" % text
    for progress in range(0, 100):
        set_job_property("progress", progress)
        sleep(0.2)

def test2(job):
    return job.progress

def test3(job, run_time, retval=None):
    print "-> callback for test2() -> %s" % retval

sched = Scheduler(origin='node1')
sched.add_jobstore(SQLAlchemyJobStore(url='sqlite://'), 'sqlite')
sched.start()

# The job will be executed on November 6th, 2009 at 16:30:05
when = datetime.now() + timedelta(seconds=2)
j1 = sched.add_date_job(test1, when, ['Mongobongo'])
j2 = sched.add_interval_job(test2, args=[j1], seconds=3, callback=test3)

try:
    print "Scheduling..."

    while True:
        sleep(10)

except KeyboardInterrupt:
    pass

print "Shutting down"
sched.shutdown()
