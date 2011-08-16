# -*- coding: utf-8 -*-
import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Sequence
from sqlalchemy.orm import relationship, backref

from libinst.entities import Base, UseInnoDB
from libinst.entities.release import Release


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
