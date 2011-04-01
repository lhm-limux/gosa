import os
import gobject
import dbus.service
import subprocess
from datetime import datetime
from subprocess import Popen, PIPE
from gosa.common.env import Environment
from gosa.common.utils import get_timezone_delta
from gosa.common.components.plugin import Plugin
from gosa.common.components.command import Command
from gosa.dbus.utils import get_system_bus


class PuppetDbusHandler(dbus.service.Object, Plugin):
    """ Puppet handler containing methods to be exported to DBUS """

    def __init__(self):
        conn = get_system_bus()
        dbus.service.Object.__init__(self, conn, '/com/gonicus/gosa/puppet')
        self.env = Environment.getInstance()

    @dbus.service.method('com.gonicus.gosa', in_signature='', out_signature='i')
    def run_puppet(self):
        """ Perform a puppet run using the current configuration """
        self.env.log.info("executing puppet")

        command = "%s -d %s" % (
            self.env.config.getOption("command", "puppet", default="/usr/bin/puppet"),
            self.env.config.getOption("manifest", "puppet", default="/etc/puppet/manifests/site.pp"),
            )
        self.env.log.debug("running puppet: %s" % command)

        msg = Popen(command, stdout=PIPE, stderr=PIPE, shell=True).stderr.read()
        hostname = self.env.id
        logdir = self.env.config.getOption("report-dir", "puppet", "/var/log/puppet")

        # Create yaml report in case of critical errors
        if msg != "":
            now = datetime.now()
            ftime = now.strftime("%Y-%m-%d %H:%M:%S.%f %z") + \
                get_timezone_delta()

            # Create structure if missing
            output_dir = logdir + "/" + hostname
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Write yaml file
            output_file = output_dir + "/" + now.strftime("%Y%m%d%H%M.yaml")
            with open(output_file, "w") as f:
                f.write("""--- !ruby/object:Puppet::Transaction::Report
  external_times: {}
  host: %(hostname)s
  logs:
    - !ruby/object:Puppet::Util::Log
      level: !ruby/sym critical
      message: %(message)s
      source: Puppet
      tags:
        - critical
      time: %(time)s
      version: &id001 2.6.0
""" % {'hostname':hostname, 'message':msg, 'time':ftime})

            self.env.log.error("running puppet failed, see '%s' for more information" % output_file)
            return False

        self.env.log.debug("running puppet succeeded")
        return True
