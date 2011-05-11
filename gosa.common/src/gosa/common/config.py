# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: config.py 1065 2010-10-08 12:35:21Z cajus $$

 This is the configuration handler of the GOsa AMQP agent. It stores
 information about the available command line options and merges them
 with the provided ini-style configuration file.

 See LICENSE for more information about the licensing.
"""
import ConfigParser
import os
import sys
import platform
from optparse import OptionParser, OptionGroup, OptionValueError
from gosa.common import __version__ as VERSION

# Only import pwd/grp stuff if we're not on windows
if platform.system() != "Windows":
    import pwd
    import grp

class ConfigNoFile(Exception):
    """
    Exception to inform about non existing or not accessible
    configuration files.
    """
    pass


class Config(object):
    """
    Configuration object storing and providing all property information.
    """
    __registry = {'core': {
                    'foreground': False,
                    'pidfile': '/var/run/gosa/gosa.pid',
                    'loglevel': 1,
                    'profile': 0,
                    'log': 'syslog',
                    'logfile': None,
                    'umask': 0o002,
                }
            }
    __configKeys = None

    def __init__(self,  config="/etc/gosa/config",  noargs=False):
        """
        Construct a new Config object. A reference is normally passed to every
        plugin instance.
        """
        # Load default user name for config parsing
        self.__registry['core']['config'] = config
        self.__noargs = noargs
        user = 'gosa'
        group = 'gosa'
        userHome = '/var/lib/gosa'

        if platform.system() != "Windows":
            try:
                userHome = pwd.getpwnam(user).pw_dir
                group = grp.getgrgid(pwd.getpwnam(user).pw_gid).gr_name
            except KeyError:
                pass

            self.__registry['core']['user'] = user
            self.__registry['core']['group'] = group
            self.__registry['core']['workdir'] = userHome

        # Load file configuration
        # TODO: remove double parsing of CmdOptions, get --config
        #       directly
        if not self.__noargs:
            self.__parseCmdOptions()
        self.__parseCfgOptions()

        # Overload with command line options
        if not self.__noargs:
            self.__parseCmdOptions()

    def __setLogLevel(self, option, opt_str, value, parser):
        levelMap = {0: "INFO", 1: "WARNING", 2: "ERROR",
                    3: "CRITICAL", 4: "DEBUG"}
        if value in levelMap:
            setattr(parser.values, option.dest, levelMap[value])
        else:
            raise OptionValueError("loglevel needs to be < %d" % len(levelMap))

    def __parseCmdOptions(self):
        parser = OptionParser(usage="%prog - the GOsa core daemon",
                    version="%prog " + VERSION)

        parser.add_option("-c", "--config", dest="config",
                          default="/etc/gosa/config",
                          help="read configuration from FILE [%default]",
                          metavar="FILE")
        parser.add_option("-f", action="store_true", dest="foreground",
                          help="run daemon in foreground [%default]")
        parser.add_option("-u", "--user", dest="user",
                          help="run daemon as USER [%default]",
                          metavar="USER")
        parser.add_option("-g", "--group", dest="group",
                          help="run daemon as GROUP [%default]",
                          metavar="GROUP")
        parser.add_option("-p", "--pid-file", dest="pidfile",
                          help="store PID information into FILE [%default]",
                          metavar="FILE")
        parser.add_option("--profile", action="store_true", dest="profile",
                          help="write profiling information (only if daemon runs in foreground mode [%default]")

        logging = OptionGroup(parser, "Logging options")
        logging.add_option("-v", "--log-level", dest="loglevel", type="int",
                          action="callback", callback=self.__setLogLevel,
                          help="log level 0 - INFO, 1 - WARNING, 2 - ERROR, 4 - CRITICAL, 5 - DEBUG")
        logging.add_option("-l", "--log-mode", dest="log",
                          help="method used for logging (syslog, stderr, file) [%default]",
                          metavar="METHOD")
        logging.add_option("--log-file", dest="logfile",
                          help="if the file method is used, log to FILE",
                          metavar="FILE")
        parser.add_option_group(logging)

        group = OptionGroup(parser, "Advanced options")
        group.add_option("--umask", dest="umask",
                          help="run daemon with UMASK [%default]",
                          metavar="UMASK")
        group.add_option("--workdir", dest="workdir",
                          help="change directory to DIR after starting up [%default]",
                          metavar="DIR")
        parser.add_option_group(group)

        (options, args) = parser.parse_args()
        items = options.__dict__
        self.__registry['core'].update(dict([(k, items[k]) for k in items if items[k] != None]))

    def getSections(self):
        """
        Return the list of available sections in the ini file. There should be at
        least 'core' available.

        @rtype: list
        @return: a list of section names
        """
        return self.__registry.keys()

    def getOptions(self, section):
        """
        Return the list of provided option names in the specified section of the
        ini file.

        @type section: str
        @param section: section name in the ini file

        @rtype: list
        @return: a list of section names
        """
        return self.__registry[section.lower()]

    def getOption(self, name, section='core', default=None):
        """
        Return the value of the option named 'name' in section 'section'. It
        can use the default value if the option does not exist.

        @type name: str
        @param name: option name

        @type section: str
        @param section: section name in the ini file, defaults to 'core'

        @type default: str
        @param section: default value to override a non existing option

        @rtype: str
        @return: content or default
        """

        # Return default - eventually
        if not section.lower() in self.__registry:
            return default
        if not name.lower() in self.__registry[section.lower()]:
            return default

        return self.__registry[section.lower()][name.lower()]

    def __getCfgFiles(self, dir):
        conf = re.compile(r"^[a-z0-9_.-]+\.conf$", re.IGNORECASE)
        try:
            return [os.path.join(dir,file)
                for file in os.listdir(dir)
                if os.path.isfile(os.path.join(dir, file)) and conf.match(file)]
        except:
            return []

    def __parseCfgOptions(self):
        # Is there a configuration available?
        configFile = self.getOption('config')
        configFiles = self.__getCfgFiles(configFile + ".d")

        config = ConfigParser.ConfigParser()
        filesRead = config.read(configFile, *configFiles)

        # Bail out if there's no configuration file
        if not filesRead:
            raise ConfigNoFile("No usable configuration file (%s) found!" % configFile)

        # Walk thru core configuration values and push them into the registry
        for section in config.sections():
            if not section in self.__registry:
                self.__registry[section] = {}
            self.__registry[section].update(config.items(section))
