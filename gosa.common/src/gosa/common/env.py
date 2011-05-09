# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: env.py 1058 2010-10-08 10:04:53Z cajus $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
import log
import config
import platform
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import *
from gosa.common.utils import dmi_system


class Environment:
    """
    The Environment container keeps logging, configuration, locking, threads
    and several informations that may be useful.

    @type id: str
    @ivar id: the node name

    @type threads: dict
    @ivar threads: list of running worker threads

    @type locks: dict
    @ivar locks: list of global thread locks

    @type config: config
    @ivar config: the L{Config} object

    @type log: log
    @ivar log: the L{Log} object
    """
    threads = []
    locks = []
    id = None
    config = None
    log = None
    domain = ""
    config = None
    noargs = False
    __instance = None
    __db = {}

    def __init__(self):
        """
        Construct a new Environment object. A reference is passed to every
        plugin instance.
        """

        # Load configuration
        self.config = config.Config(config=Environment.config,  noargs=Environment.noargs)
        self.log = log.getLogger(
                logtype=self.config.getOption("log"),
                logfile=self.config.getOption("logfile"),
                loglevel=self.config.getOption("loglevel"))

        self.id = platform.node()
        self.log.info("server id %s" % self.id)

        # Dump configuration
        if self.config.getOption("loglevel") == "DEBUG":
            self.log.debug("configuration dump:")

            for section in self.config.getSections():
                self.log.debug("[%s]" % section)
                items = self.config.getOptions(section)

                for item in items:
                    self.log.debug("%s = %s" % (item, items[item]))

            self.log.debug("end of configuration dump")

        # Initialized
        self.domain = self.config.getOption("domain", default="org.gosa")
        self.uuid = self.config.getOption("id", default=None)
        if not self.uuid:
            self.log.warning("system has no id - falling back to configured hardware uuid")
            self.uuid = dmi_system("uuid")

            if not self.uuid:
                self.log.error("system has no id - please configure one in the core section")
                raise Exception("No system id found")

        self.active = True

    def getDatabaseEngine(self, section, key="database"):
        """
        Return a database engine based on configuration section/key.

        @type section: string
        @param section: configuration section to look for database string

        @type key: string
        @param key: key to look for in specified section, defaults to "database"

        @rtype: Engine
        @return: sqlalchemy engine object
        """
        index = "%s/%s" % (section, key)

        if not index in self.__db:
            self.__db[index] = create_engine(self.config.getOption(key, section),
                    pool_size=40, pool_recycle=120)

        return self.__db[index]

    def getDatabaseSession(self, section, key="database"):
        sql = self.getDatabaseEngine(section, key)
        session = scoped_session(sessionmaker(autoflush=True))
        session.configure(bind=sql)
        return session()

    @staticmethod
    def getInstance():
        if not Environment.__instance:
            Environment.__instance = Environment()
        return Environment.__instance
