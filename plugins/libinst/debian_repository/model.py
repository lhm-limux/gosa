# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: model.py 1321 2010-10-28 20:58:18Z cajus $$

 See LICENSE for more information about the licensing.
"""

from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence, Text
from sqlalchemy.orm import relationship, create_session

from libinst.repository import Base, Package, Distribution, Architecture, Section, Release, Component, UseInnoDB
import os
import subprocess
import gettext
import select
from gosa.common.utils import N_, locate
from gosa.common.env import Environment
# pylint: disable-msg=E0611
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("debian_repository", "locale"), fallback=True)
_ = t.ugettext

class DebianPriority(Base, UseInnoDB):
    __tablename__ = 'debian_priority'
    id = Column(Integer, Sequence('debian_priority_id_seq'), primary_key=True)
    name = Column(String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def getInfo(self):
        return {
            "name": self.name,
        }


class DebianPackage(Package, UseInnoDB):
    __tablename__ = 'debian_package'
    __mapper_args__ = {'polymorphic_identity': 'debian_package'}
    id = Column(Integer,
                Sequence('debian_package_id_seq'),
                ForeignKey('package.id'),
                primary_key=True)
    package = relationship(Package)
    source = Column(String(255))
    maintainer = Column(String(255))
    installed_size = Column(String(255))
    depends = Column(Text)
    build_depends = Column(Text)
    format = Column(Text)
    standards_version = Column(Text)
    recommends = Column(Text)
    suggests = Column(Text)
    provides = Column(Text)
    priority_id = Column(Integer, ForeignKey('debian_priority.id'))
    priority = relationship(DebianPriority)
    long_description = Column(Text)

    def __repr__(self):
        return super(DebianPackage, self).__repr__()

    def getInfo(self):
        result = super(DebianPackage, self).getInfo()
        result.update({
            "source": self.source,
            "maintainer": self.maintainer,
            "installed_size": self.installed_size,
            "depends": self.depends,
            "build_depends": self.build_depends,
            "format": self.format,
            "standards_version": self.standards_version,
            "recommends": self.recommends,
            "suggests": self.suggests,
            "provides": self.provides,
            # pylint: disable-msg=E1101
            "priority": None if not self.priority else self.priority.name,
            "long_description": self.long_description,
        })
        return result


class DebianComponent(Component, UseInnoDB):
    __mapper_args__ = {'polymorphic_identity': 'debian_component'}


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


class DebianRelease(Release, UseInnoDB):
    __mapper_args__ = {'polymorphic_identity': 'debian_release'}
    codename = Column(String(255))

    def getInfo(self):
        result = super(DebianRelease, self).getInfo()
        result.update({
            "codename": self.codename,
        })
        return result

    def _initDirs(self):
        # pylint: disable-msg=E1101
        path = self.distribution.repository.path
        # pylint: disable-msg=E1101
        dists_path = os.sep.join((path, self.distribution.name, "dists"))
        # pylint: disable-msg=E1101
        pool_path = os.sep.join((path, "pool", self.distribution.type.name))

        if not os.path.exists(dists_path) and os.access(path, os.W_OK):
            os.makedirs(dists_path)
        if not os.path.exists(pool_path) and os.access(path, os.W_OK):
            os.makedirs(pool_path)

        self_path = os.sep.join((dists_path, self.name.replace('/', os.sep)))
        if not os.path.exists(self_path) and os.access(path, os.W_OK):
            os.makedirs(self_path)

        for component in self.distribution.components:
            if not os.path.exists(os.sep.join((self_path, component.name))) and os.access(path, os.W_OK):
                os.mkdir(os.sep.join((self_path, component.name)))

            for architecture in self.distribution.architectures:
                if architecture.name == "source":
                    if not os.path.exists(os.sep.join((self_path, component.name, architecture.name))) and os.access(path, os.W_OK):
                        os.mkdir(os.sep.join((self_path, component.name, architecture.name)))
                else:
                    if not os.path.exists(os.sep.join((self_path, component.name, "binary-" + architecture.name))) and os.access(path, os.W_OK):
                        os.mkdir(os.sep.join((self_path, component.name, "binary-" + architecture.name)))


    def _rename(self, target_name):
        self.name = target_name
        # pylint: disable-msg=E1101
        for child in self.children:
            child._rename(self.name + "/" + child.name.rsplit('/', 1)[1])


    def _sync(self):
        # pylint: disable-msg=E1101
        pool_path = os.sep.join((self.distribution.repository.path, "pool", self.distribution.type.name))
        try:
            # pylint: disable-msg=E1101
            for package in self.packages:
                # pylint: disable-msg=E1101
                pkg_path = os.sep.join((pool_path, package.component.name, package.name[:3] if package.name.startswith('lib') else package.name[0], package.name))
                # pylint: disable-msg=E1101
                path = os.sep.join((self.distribution.path, "dists",  self.name.replace('/', os.sep), package.component.name))
                # pylint: disable-msg=E1101
                if package.type.name == 'deb':
                    # pylint: disable-msg=E1101
                    path += os.sep + "binary-" + package.arch.name
                if not os.path.exists(path):
                    os.makedirs(path)
                # pylint: disable-msg=E1101
                if not os.path.exists(path + os.sep + package.file.name):
                    current_dir = os.getcwd()
                    os.chdir(path)
                    # pylint: disable-msg=E1101
                    os.symlink(os.path.relpath(pkg_path + os.sep + package.file.name), package.file.name)
                    os.chdir(current_dir)
            return True
        except:
            return False
