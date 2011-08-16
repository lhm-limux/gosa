# -*- coding: utf-8 -*-
import re
import os
import dbus
import pyinotify
import ConfigParser
import yaml
import socket
from shutil import rmtree
from fcntl import lockf, LOCK_UN, LOCK_EX
from git import Repo
from pwd import getpwnam
from time import mktime, sleep

from gosa.common.event import EventMaker
from gosa.common.components import Plugin
from gosa.common.components import Command
from gosa.common import Environment
from gosa.common.components.registry import PluginRegistry

# Add constructor to parse ruby data type
def rubysym(loader, node):
    value = loader.construct_scalar(node)
    return value

yaml.add_constructor(u'!ruby/sym', rubysym)

# To make this work on windows, tool at that code:
# http://tgolden.sc.sabren.com/python/win32_how_do_i/watch_directory_for_changes.html


class PuppetClient(Plugin):
    """
    This class provides the client side of being puppet enabled. That
    is mainly

     - provide a git data store
     - provide an update hook to move the changes to the target dir
     - add ssh keys that are allowed to push config data
    """

    _target_ = 'puppet'

    def __init__(self):
        env = Environment.getInstance()
        self.env = env

        # Read config values
        self.__puppet_user = env.config.get("puppet.user",
            default=env.config.get("client.user", default="gosa"))
        self.__target_dir = env.config.get("puppet.target", default="/etc/puppet")
        self.__puppet_command = env.config.get("puppet.command", default="/usr/bin/puppet")
        self.__report_dir = env.config.get("puppet.report-dir", default="/var/log/puppet")

        self.__base_dir = getpwnam(self.__puppet_user).pw_dir

        # Initialize if not already done
        if not self.puppetIsInitialized():
            self.puppetInitialize(True)

        # Start log listener
        wm = pyinotify.WatchManager()
        # pylint: disable-msg=E1101
        wm.add_watch(self.__report_dir, pyinotify.IN_CREATE, rec=True, auto_add=True)

        notifier = pyinotify.ThreadedNotifier(wm, PuppetLogWatcher())
        env.threads.append(notifier)

        notifier.start()

    @Command()
    def puppetListKeys(self):
        """ List available puppet keys """
        result = {}

        # Read authorize file and extract keys
        try:
            with open(self.__base_dir + "/.ssh/authorized_keys") as f:
                content = f.readlines()
        except IOError:
            self.env.log.warn("No authorized keys available in '%s'" % \
                self.__base_dir + "/.ssh/authorized_keys")
            return result

        # Clean lines and extract info
        for line in [re.sub(r"\s{2,}", " ", c.strip()) for c in content]:
            (key_type, key_data, key_id) = line.split(" ")[3:6]
            result[key_id] = {'type': key_type, 'data': key_data}

        return result

    @Command()
    def puppetAddKey(self, key):
        """ Add SSH key to the list of puppet keys """
        if not self.puppetIsInitialized():
            self.puppetInitialize()

        (key_type, key_data, key_id) = re.sub(r"\s{2,}", " ", key).split(" ")

        # Load keys
        keys = self.puppetListKeys()
        if key_id in keys:
            raise ValueError("Key id '%s' already exist" % key_id)

        # Add key
        self.env.log.info("adding puppet key '%s'" % key_id)
        keys[key_id] = {'type': key_type, 'data': key_data}
        self.__write_keys(keys)

    @Command()
    def puppetDelKey(self, id):
        """ Delete SSH key from the list of puppet keys """
        if not self.puppetIsInitialized():
            raise ValueError("No keys available")

        # Load keys
        keys = self.puppetListKeys()
        if not id in keys:
            raise ValueError("Key id '%s' does not exist" % id)

        # Del key
        self.env.log.info("removing puppet key '%s'" % id)
        del keys[id]
        self.__write_keys(keys)

    @Command()
    def puppetInitialize(self, purge=False):
        """ (Re-) initialize client side puppet data stores """
        ssh_path = self.__base_dir + "/.ssh"
        git_path = self.__base_dir + "/data.git"

        # Eventually purge old data
        if purge:
            self.env.log.info("puring git and ssh infrastructure")
            if os.path.exists(ssh_path):
                rmtree(ssh_path)
            if os.path.exists(git_path):
                rmtree(git_path)

            # Clean __target_dir without removing it
            if os.path.exists(self.__target_dir):
                for root, dirs, files in os.walk(self.__target_dir):
                    for f in files:
                        os.unlink(os.path.join(root, f))
                    for d in dirs:
                        rmtree(os.path.join(root, d))

        self.env.log.info("initializing git and ssh infrastructure")

        # Create .ssh container if it does not exist
        if not os.path.exists(ssh_path):
            self.env.log.debug("creating %s" % ssh_path)
            os.mkdir(ssh_path, 0770)

        # Create target directory
        if not os.path.exists(self.__target_dir):
            self.env.log.debug("creating %s" % self.__target_dir)
            os.mkdir(self.__target_dir, 0770)

        # Create git container if it does not exist
        if not os.path.exists(git_path):
            # Initialize a bare git repository
            self.env.log.debug("creating bare git repository at '%s'" % git_path)
            repo = Repo.init_bare(git_path)
            os.chmod(git_path, 0770)

            # Create post-update hook
            self.env.log.debug("installing post-update hook")
            with open(git_path + "/hooks/post-update", "w") as f:
                f.write("#!/bin/sh\ngit archive --format=tar HEAD | (cd %s && tar xf -)\ndbus-send --system --type=method_call --dest=com.gonicus.gosa /com/gonicus/gosa/puppet com.gonicus.gosa.run_puppet" % self.__target_dir)

            os.chmod(git_path + "/hooks/post-update", 0755)

    @Command()
    def puppetRun(self):
        """ Perform a manual puppet run """
        self.env.log.debug("calling dbus run_puppet method")
        bus = dbus.SystemBus()
        gosa_dbus = bus.get_object('com.gonicus.gosa', '/com/gonicus/gosa/puppet')
        return bool(gosa_dbus.run_puppet(dbus_interface = "com.gonicus.gosa"))

    @Command()
    def puppetGetReleaseInfo(self):
        """ Retrieve clients release info """
        if not self.puppetIsInitialized():
            raise ValueError("Client not initialized")

        release_info = self.__target_dir + "/release.info"
        if not os.path.exists(release_info):
            raise ValueError("No release information available")

        # Parse release.info
        config = ConfigParser.ConfigParser()
        config.read(release_info)

        return {
            'distribution': config.get('release', 'distribution'),
            'version': config.get('release', 'version'),
            'description': config.get('release', 'description'),
            }

    @Command()
    def puppetIsInitialized(self):
        """ Check if client is initialized """
        return os.path.exists(self.__base_dir + "/.ssh") and \
            os.path.exists(self.__base_dir + "/data.git")

    @Command()
    def puppetGetPushPath(self):
        """ Get path where the configuration has to be pushed to """
        user = self.env.config.get('client.user', default="gosa")
        fqdn = socket.gethostbyaddr(self.env.id)[0]
        return "%s@%s:%s" % (user, fqdn, self.__base_dir + "/data.git")

    def __write_keys(self, keys):
        self.env.log.debug("writing authorized_keys")
        with open(self.__base_dir + "/.ssh/authorized_keys", "w") as f:
            lockf(f, LOCK_EX)
            for id, key in keys.iteritems():
                f.write("command=\"git-shell -c \\\"$SSH_ORIGINAL_COMMAND\\\"\" %s %s %s" % (key['type'], key['data'], id))
            lockf(f, LOCK_UN)


class PuppetLogWatcher(pyinotify.ProcessEvent):

    def __init__(self):
        self.env = Environment.getInstance()

    def process_IN_CREATE(self, event):
        self.env.log.debug("logwatch detected change for '%s'" % event.pathname)
        if event.pathname.endswith(".yaml"):
            sleep(1)
            amqp = PluginRegistry.getInstance("AMQPClientHandler")
            self.env.log.debug("puppet logwatch detected change for '%s', producing event" % event.pathname)
            amqp.sendEvent(self.report_to_event(event.pathname))

    def report_to_event(self, file_name):
        e = EventMaker()
        amqp_service = PluginRegistry.getInstance("AMQPClientService")

        with open(file_name, "r") as f:
            yml = yaml.load(f)
            logs = [e.Id(self.env.id)]

            for log in yml.logs:
                data = [
                    e.Timestamp(str(mktime(log.time.timetuple()))),
                    e.Level(log.level),
                    e.Message(log.message),
                ]

                # Append tags
                #TODO: Fix XML schema to keep tags
                #for tag in log.tags:
                #    data.append(e.Tag(tag))

                # Add optional tags
                try:
                    data.append[e.Source(log.source)]
                except:
                    pass
                try:
                    data.append[e.Line(log.line)]
                except:
                    pass
                try:
                    data.append[e.File(log.file)]
                except:
                    pass
                try:
                    data.append[e.Version(log.version)]
                except:
                    pass

                logs.append(e.PuppetLog(*data))

        return e.Event(e.PuppetReport(*logs))


class PuppetReport(yaml.YAMLObject):
    yaml_tag = u'!ruby/object:Puppet::Transaction::Report'


class PuppetLog(yaml.YAMLObject):
    yaml_tag = u'!ruby/object:Puppet::Util::Log'


class PuppetMetric(yaml.YAMLObject):
    yaml_tag = u'!ruby/object:Puppet::Util::Metric'
