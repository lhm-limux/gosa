# -*- coding: utf-8 -*-
"""
TODO: docs
"""
from zope.interface import implements
from gosa.common.handler import IInterfaceHandler
from gosa.common import Environment
from gosa.common.utils import N_
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

        #TODO: add event listener for remote schedulers

    def stop(self):
        """ Stop scheduler service. """
        self.sched.shutdown()

    def migrate(self):
        """
        Migration "cron" job.
        """
        self.env.log.debug("scheduler: looking for stale jobs")
        #TODO: realy look for stale jobs
        #self.sched.reschedule()

    @Command(__help__=N_("Return scheduler information for a specific job."))
    def schedulerGetJob(self, job_id):
        return self.sched.get_job_by_id(job_id)

    @Command(__help__=N_("List jobs matchings an optional filter."))
    def schedulerGetJobs(self, fltr=None):
        res = {}

        for job in self.sched.get_jobs():
            res[job.uuid] = []

        return res

    @Command(needsUser=True, __help__=N_("Add a new job to the scheduler."))
    def schedulerAddJob(self, user):
    #def add_job(self, trigger, func, args, kwargs, jobstore='default',
    #            **options):
    #    """
    #    Adds the given job to the job list and notifies the scheduler thread.

    #    :param trigger: alias of the job store to store the job in
    #    :param func: callable to run at the given time
    #    :param args: list of positional arguments to call func with
    #    :param kwargs: dict of keyword arguments to call func with
    #    :param jobstore: alias of the job store to store the job in
    #    :rtype: :class:`~gosa.common.components.scheduler.job.Job`
    #    """
    # Options:
    # * misfire_grace_time
    # * coalesce
    # * name
    # * max_runs
    # * max_instances
    # * tag
    # * owner
    # * description
    # * callback
        #return job.uuid
        pass

    @Command(needsUser=True, __help__=N_("Add a new job to the scheduler."))
    def schedulerUpdateJob(self, user, job_id):
        pass

    @Command(needsUser=True, __help__=N_("Remove job from the scheduler."))
    def schedulerRemoveJob(self, user, job_id):
        pass
