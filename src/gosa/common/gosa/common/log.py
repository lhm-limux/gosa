# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: log.py 608 2010-08-16 08:12:35Z cajus $$

 See LICENSE for more information about the licensing.
"""
import os
import sys
import logging
import logging.handlers


class NullHandler(logging.Handler):
    """
    Dummy handler which is used if logging is completely disabled.
    """
    def emit(self, record):
        pass


def getLogger(logtype='syslog', logfile=None, loglevel=None, logid='GOsa'):
    """
    Return a logger instance based on type, file, id and loglevel.

    @type logtype: str
    @param logtype: how logging takes place (file, syslog, unix, stderr)

    @type logfile: str
    @param logfile: filename to use if logtype is "file"

    @type loglevel: str
    @param loglevel: how verbose to log (ALL/DEBUG, INFO, WARNING, ERROR, CRITICAL)

    @type logid: str
    @param logid: mark messages with the 'logid'
    """
    logger = logging.getLogger(logid)
    logtype = logtype.lower()
    if not loglevel:
        loglevel = "WARNING"

    # Set handler according to the logtype
    if logtype == 'file':
        handler = logging.FileHandler(logfile)
    elif logtype in ('syslog', 'unix'):
        handler = logging.handlers.SysLogHandler('/dev/log')
    elif logtype == 'stderr':
        handler = logging.StreamHandler(sys.stderr)
    elif logtype == 'eventlog':
        handler = logging.handlers.NTEventLogHandler(sys.argv[0])
    else:
        handler = NullHandler()

    level = loglevel.upper()
    if level in ('DEBUG', 'ALL'):
        logger.setLevel(logging.DEBUG)
    elif level == 'INFO':
        logger.setLevel(logging.INFO)
    elif level == 'ERROR':
        logger.setLevel(logging.ERROR)
    elif level == 'CRITICAL':
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.WARNING)

    formatter = logging.Formatter('%(levelname)s: %(module)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger._handler = handler

    return logger
