# -*- coding: utf-8 -*-
"""
TODO: docs
"""
from zope.interface import implements
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.common.components.scheduler import Scheduler, set_job_property
from gosa.common.components.scheduler.jobstores.sqlalchemy_store import SQLAlchemyJobStore

class SchedulerService(object):
    """
    TODO: docs
    """
    implements(IInterfaceHandler)
    _priority_ = 0

    # Target queue
    _target_ = 'core'

    def __init__(self):
        env = Environment.getInstance()
        env.log.debug("initializing scheduler")
        self.env = env

        self.sched = Scheduler(origin=self.env.id)
        self.sched.add_jobstore(SQLAlchemyJobStore(
            engine=env.getDatabaseEngine('scheduler'),
            tablename='scheduler_jobs'), 'db')

    def serve(self):
        """
        Start the scheduler service.
        """
        self.sched.start()

        # Start migration job
        self.sched.add_interval_job(self.migrate, seconds=60)

    def stop(self):
        """ Stop scheduler service. """
        sched.shutdown()

    def migrate(self):
        """
        Migration "cron" job.
        """
        self.env.log.debug("scheduler: looking for stale jobs")
        #TODO: realy look for stale jobs
