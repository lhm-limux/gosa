# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: repository.py 1264 2010-10-22 12:28:49Z janw $$

 See LICENSE for more information about the licensing.
"""
import gettext
import os
import select
import subprocess

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.distribution import Distribution

from gosa.common.env import Environment
from gosa.common.utils import N_, locate

# pylint: disable-msg=E0611
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("libinst.repo.deb", "locale"), fallback=True)
_ = t.ugettext

class DebianDistribution(Distribution, UseInnoDB):
    __tablename__ = 'debian_distribution'
    __mapper_args__ = {'polymorphic_identity': 'debian_distribution'}
    id = Column(Integer,
                Sequence('debian_distribution_id_seq'),
                ForeignKey('distribution.id'),
                primary_key=True)
    debian_security = Column(String(255))
    debian_volatile = Column(String(255))

    def getInfo(self):
        result = super(DebianDistribution, self).getInfo()
        result.update({
            "debian_security": self.debian_security,
            "debian_volatile": self.debian_volatile,
        })
        return result

    def _sync(self):
        #TODO: fix endless loops, fix repository update
        return

        env = Environment.getInstance()
        self.env = env
        result = True
        arch = None
        # pylint: disable-msg=E1101
        if self.managed==False and self.repository:
            if not locate("debmirror"):
                raise ValueError(N_("The command {command} was not found in $PATH").filter(command="debmirror"))

            # pylint: disable-msg=E1101
            if self.origin.startswith(('http://', 'https://', 'ftp://')):
                if not self.architectures:
                    raise ValueError(N_("No architectures specified. Please add architectures to this distribution"))
                if not self.components:
                    raise ValueError(N_("No components specified. Please add components to this distribution"))

                method, host = self.origin.split('://')
                host, path = host.split('/', 1)
                proxy = ""
                command = "debmirror --ignore-small-errors --ignore-missing-release --ignore-release-gpg --progress"
                command += " --host=%s" % host
                command += " --method=%s" % method
                command += " --root=%s" % path
                command += " --dist=%s" % ','.join([str(x) for x in self.releases])
                command += " --arch=%s" % ','.join([str(x) for x in self.architectures])
                command += " --section=%s" % ','.join([str(x) for x in self.components])
                if proxy:
                    command += " --proxy='%s'" % proxy
                if self.mirror_sources:
                    command += " --source"
                else:
                    command += " --nosource"
                command += " " + self.repository.path + os.sep + self.name
                p = subprocess.Popen(command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                while not p.poll():
                    for triple in select.select([p.stdout, p.stderr], [], []):
                        if triple:
                            if triple[0].fileno() == p.stdout.fileno():
                                self.env.log.debug(p.stdout.readline().rstrip())
                            else:
                                self.env.log.error(p.stderr.readline().rstrip())
        elif self.managed==True and self.repository:
            for release in self.releases:
                result = result and release._sync()
        return result
