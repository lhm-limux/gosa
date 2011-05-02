# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: manage.py 1277 2010-10-22 14:31:42Z janw $$

 See LICENSE for more information about the licensing.
"""
# pylint: disable=E0611
from pkg_resources import resource_filename

import os
import shutil
import hashlib
import tempfile
import urllib2
import pkg_resources
import gnupg
import re
import pytz
import gettext
import ldap
from types import StringTypes, DictType
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from libinst.entities import Base
from libinst.entities.architecture import Architecture
from libinst.entities.component import Component
from libinst.entities.config_item import ConfigItem, ConfigItemReleases
from libinst.entities.distribution import Distribution
from libinst.entities.file import File
from libinst.entities.package import Package
from libinst.entities.release import Release
from libinst.entities.repository import Repository, RepositoryKeyring
from libinst.entities.section import Section
from libinst.entities.type import Type
from libinst.system_locale import locale_map
from libinst.keyboard_models import KeyboardModels
from libinst.methods import load_system

from gosa.common.env import Environment
from gosa.common.components.command import Command, NamedArgs
from gosa.agent.ldap_utils import LDAPHandler
from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_

# Include locales
t = gettext.translation('messages', resource_filename("libinst", "locale"), fallback=True)
_ = t.ugettext

ALLOWED_CHARS_RELEASE = "^[A-Za-z0-9\-_\.\/]+$"
ALLOWED_CHARS_DISTRIBUTION = "^[A-Za-z0-9\-_\.]+$"

#TODO: @Command decorators need to be configured for making
#      it multi-server aware. But this feature has to be tested
#      completely.

#TODO: ATM a host must have a dedicated database, path is not specific enough
#      to identify hosts. What about other plugins?

class RepositoryManager(Plugin):
    """ The RepositoryManager allows managing several types of repositories.

        Example usage:
        ...
    """
    _target_ = 'libinst'
    recipeRecursionDepth = 3

    def __init__(self):
        """
        Construct a new RepositoryManager instance based on the configuration
        stored in the environment.

        @type env: Environment
        @param env: L{Environment} object
        """
        env = Environment.getInstance()
        self.env = env
        engine = env.getDatabaseEngine("repository")
        Session = scoped_session(sessionmaker(autoflush=True, bind=engine))
        self._session = Session()
        self.path = env.config.getOption('path', section='repository')

        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except:
                raise

        # Load all repository handlers
        self.type_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.repository"):
            module = entry.load()
            self.env.log.info("repository handler %s included" % module.__name__)
            for module_type in module.getRepositoryTypes():
                self.type_reg[module_type] = module()

        # Load all installation methods
        self.install_method_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.methods"):
            module = entry.load()
            self.env.log.info("installation method %s included " % module.__name__)
            self.install_method_reg[module.getInfo()['name'].lower()] = module(self)

        # Load all base installation methods
        self.base_install_method_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.base_methods"):
            module = entry.load()
            self.env.log.info("base installation method %s included " % module.__name__)
            self.base_install_method_reg[module.getInfo()['name'].lower()] = module()

        # Purge DB if wanted
        db_purge = env.config.getOption('db_purge', section='repository')
        if db_purge == "True":
            self.initializeDatabase(engine)
        # Initialize internal repository instance
        self._repository = self._getRepository(path=self.path, add=True)

        # Load keyboard models
        self.keyboardModels = KeyboardModels().get_models()

    #==========================================================================
    # initialize all DB schema for an in Memory Database:
    # the parameter given here are not important
    #==========================================================================
    def initializeDatabase(self, engine):
        a = Base()
        # pylint: disable=E1101
        a.metadata.drop_all(engine)
        # pylint: disable=E1101
        a.metadata.create_all(engine)

    #TODO: This is a dummy function
    @Command(__doc__=N_("List the available base install methods"))
    def getSupportedBaseInstallMethods(self):
        for m in self.base_install_method_reg:
            print "---->", m
        return {"preseed": {
            "name": "Debian preseed",
            "description": "Base installation using the debian installer",
            "repositories": ["deb"],
            "methods": ["puppet"]},
            }

    @Command(__doc__=N_("List the available installation methods"))
    def getSupportedInstallMethods(self):
        import copy
        methods = {}
        for method, obj in self.install_method_reg.iteritems():
            methods[method] = obj.getInfo()

            # Remove checks and modules
            #items = obj.getItemTypes()
            #for k, v in obj.getItemTypes().iteritems():
            #    if 'module' in u:
            #        del u['module']
            #    if 'options' in u and 'data' in u['options'] and 'check' in u['options']['data']:
            #        del u['options']['data']['check']
            #    items[k] = u

            methods[method]["items"] = obj.getItemTypes()
            methods[method]["repositories"] = obj.getSupportedTypes()

        return methods

    @Command(__doc__=N_("List the available repository types for this host"))
    def getSupportedRepositoryTypes(self):
        return self.type_reg.keys()

    @Command(__doc__=N_("List used repository types"))
    def getRepositoryTypes(self):
        """
        getRepositoryTypes lists all available repository types like
        i.e. 'deb', 'rpm', etc.

        @rtype: dict
        @return: dictionary containing types and discriptions of available
                 repository types.
        """
        return dict([(type.name, type.description)
            for type in self._session.query(Type).all()])

    @Command(__doc__=N_("Get the external Repository URL for the given Release"))
    def getMirrorURL(self, release):
        result = None
        if not self.env.config.getOption('http_base_url', section='repository'):
            raise ValueError(N_("Option 'http_base_url' in section 'repository' is not configured!"))
        distribution = self._getDistribution(release.split('/')[0])
        if distribution:
            release = release.split('/', 1)[1]
        if not self._getRelease(release):
            raise ValueError(N_("Release {release} was not found!").format(release=release))
        else:
            release = self._getRelease(release)
        result = self.env.config.getOption('http_base_url', section='repository')
        if not result.endswith('/'):
            result += '/'
        if distribution is not None:
            result += distribution.name + '/'
        else:
            result += release.distribution.name + '/'
        result += release.name
        return result

    @Command(__doc__=N_("List available distributions"))
    def getDistributions(self):
        """
        getDistributions lists all registered distributions.

        @rtype: dict
        @return: dictionary containing a list of distribution name /
                 discription pairs.
        """
        result = None
        if self._repository.distributions:
            result = [distribution.getInfo() for distribution in self._repository.distributions]
        return result

    @Command(__doc__=N_("List available releases for the given distribution"))
    @NamedArgs("m_hash")
    def getReleases(self, m_hash=None, distribution=None):
        """
        getReleases lists all registered releases for the given distribution.

        @type distribution: string
        @param distribution: distribution name

        @rtype: dict
        @return: dictionary containing a list of releases name /
                 discription pairs.
        """
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s not found" % distribution))
                else:
                    distribution = instance
            result = distribution.releases
        else:
            try:
                result = self._session.query(Release).all()
            except:
                result = None
        return None if not result else [release.getInfo() for release in result]

    @Command(__doc__=N_("List available architectures for the given distribution"))
    @NamedArgs("m_hash")
    def getArchitectures(self, m_hash=None, distribution=None, release=None):
        """
        getArchitectures lists all available architectures, optional for the
        given distribution or release.

        @type distribution: string
        @param distribution: distribution name

        @type release: string
        @param release: release name

        @rtype: list
        @return: list of architectures
        """
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                distribution = self._getDistribution(distribution)
            try:
                result = self._session.query(Distribution).filter_by(name=distribution.name).one().architectures
            except:
                result = None
        elif release:
            if isinstance(release, StringTypes):
                release = self._getRelease(release)
            try:
                result = set()
                for package in release.packages:
                    result.add(package.arch)
                result = list(result)
            except:
                result = None
        else:
            try:
                result = self._session.query(Architecture).all()
            except:
                result = None
        return [architecture.getInfo() for architecture in result]

    @Command(__doc__=N_("List available sections for the given distribution"))
    @NamedArgs("m_hash")
    def getSections(self, m_hash=None, distribution=None, release=None):
        """
        getSections lists all available sections for the given
        distribution.

        @type distribution: string
        @param distribution: distribution name

        @rtype: list
        @return: list of sections
        """
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                distribution = self._getDistribution(distribution)
            try:
                result = self._session.query(Distribution).filter_by(name=distribution.name).one().sections
            except:
                result = None
        elif release:
            if isinstance(release, StringTypes):
                release = self._getRelease(release)
            try:
                result = set()
                for package in release.packages:
                    result.add(package.section)
                result = list(result)
            except:
                result = None
        else:
            try:
                result = self._session.query(Section).all()
            except:
                result = None
        return [release.getInfo() for release in result]

    @Command(__doc__=N_("Create a new distribution based on type, mirror and installation method"))
    @NamedArgs("m_hash")
    def createDistribution(self, name, type, m_hash=None, install_method=None, mirror=None):
        """
        createDistribution creates a new distribution, optionally based on a
        specific type or mirror.

        @type name: string
        @param name: distribution name

        @type type: string
        @param type: type of distribution (i.e. 'deb, 'rpm', etc.)

        @type mirror: string
        @param mirror: Source URL for to mirror the distribution from

        @rtype: boolean
        @return: True for success
        """
        result = None

        # sanity checks
        p = re.compile(ALLOWED_CHARS_DISTRIBUTION)
        if not name:
            raise ValueError("name cannot be empty!")
            return result != None
        if not p.match(name):
            raise ValueError("%s contains invalid characters!" % name)
            return result != None
        if name == "master":
            raise ValueError("master is a reserved keyword!")
            return result != None
        if install_method is not None:
            if not type in self.install_method_reg[install_method]._supportedTypes:
                raise ValueError("Distribution Type %s is not supported by installation method %s" % (type, install_method))
                return result != None

        if not self._getDistribution(name):
            if isinstance(type, StringTypes):
                type = self._getType(type, add=True)
            if type is not None and type.name in self.type_reg:
                result = self.type_reg[type.name].createDistribution(self._session, name, mirror=mirror)
                if result is not None:
                    result.type = type
                    result.installation_method = install_method
                    self._session.add(result)
                    # pylint: disable=E1101,E1103
                    self._repository.distributions.append(result)
                    try:
                        self._session.commit()
                        result.repository._initDirs()
                    except:
                        self.env.log.error("Problem creating distribution %s" % result.name)
                        self._session.rollback()
                        result = False
                        raise
            else:
                raise ValueError("Name and Type are both needed for creating a distribution!")

        return result != None

    @Command(__doc__=N_("Remove selected distribution from the repository"))
    @NamedArgs("m_hash")
    def removeDistribution(self, distribution, m_hash=None, recursive=False):
        """
        removeDistribution removes an existing distribution. It checks the
        dependencies and will not remove a parent distribution until the
        recursive parameter is specified.

        @type name: string
        @param name: distribution name

        @type recursive: bool
        @param recursive: recursive removal of distributions

        @rtype: boolean
        @return: True for success
        """
        result = False
        if isinstance(distribution, StringTypes):
            instance = self._getDistribution(distribution)
            if not instance:
                raise ValueError(N_("Distribution %s not found", distribution))
            else:
                distribution = instance

        if distribution.releases and recursive is not True:
            raise ValueError(N_("Distribution {distribution} contains releases. Need to set recursive or remove all releases to allow removal!").format(distribution=distribution.name))
        else:
            for release in distribution.releases[:]:
                # We only remove top-level releases
                if not '/' in release.name:
                    self.env.log.debug("Removing release %s/%s" % (distribution.name,  release.name))
                    self.removeRelease(release, recursive=recursive)

        result = self.type_reg[distribution.type.name].removeDistribution(self._session, distribution, recursive=recursive)
        if result is not None:
            try:
                distribution.repository.distributions.remove(distribution)
                self._session.delete(distribution)
                self._session.commit()
                result = True
            except:
                raise
                self.env.log.error("Problem removing distribution %s" % distribution.name)
                self._session.rollback()
                result = None

        return result

    @Command(__doc__=N_("Create a new release belonging to distribution"))
    def createRelease(self, distribution, name):
        """
        createRelease creates a new release belonging to a distribution. It
        can optionally have a parent release. Parent releases are specified
        using the name field: i.e. name = 'lenny/5.0.4'

        @type distribution: string
        @param distribution: distribution name

        @type name: string
        @param name: release name

        @rtype: boolean
        @return: True for success
        """
        result = None
        if not self._getRelease(name):
            p = re.compile(ALLOWED_CHARS_RELEASE)
            if not p.match(name):
                raise ValueError(N_("Release name {release} contains invalid characters!").format(release=name))
            if name == "master":
                raise ValueError(N_("master is a reserved keyword!"))

            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if instance:
                    distribution = instance
                else:
                    raise ValueError(N_("Distribution {distribution} does not exist!").format(distribution=distribution))

            if '/' in name and not self._getRelease(name.rsplit('/', 1)[0]):
                raise ValueError(N_("Parent release {release} not found!").format(release=name.rsplit('/', 1)[0]))

            result = self.type_reg[distribution.type.name].createRelease(self._session, distribution, name)
            if result is not None:
                self._session.add(result)
                distribution.releases.append(result)
                if result.parent is not None:
                    for package in result.parent.packages[:]:
                        result.packages.append(package)
                try:
                    self._session.commit()
                    distribution.repository._initDirs()
                except:
                    self._session.rollback()
                    raise
                if result.distribution.installation_method is not None:
                    try:
                        self.install_method_reg[result.distribution.installation_method].createRelease(result.name, result.parent)
                    except:
                        raise
        else:
            raise ValueError(N_("Release {release} already exists!").format(release=name))
        return result != None

    @Command(__doc__=N_("Remove a release"))
    @NamedArgs("m_hash")
    def removeRelease(self, release, m_hash=None, recursive=False):
        """
        removeRelease removes an existing release and - if recursive is specified -
        the sub-releases.

        @type release: string
        @param release: release name

        @type recursive: bool
        @param recursive: True to remove sub releases

        @rtype: boolean
        @return: True for success
        """
        result = None
        if isinstance(release, StringTypes):
            instance = self._getRelease(release)
            if not instance:
                raise ValueError(N_("Release %s not found" % release))
            else:
                release = instance
        if release.children and recursive is not True:
            raise ValueError("Won't remove a parent release without being recursived!")
        elif release.children and recursive is True:
            for child_release in release.children[:]:
                self.env.log.debug("Removing child release %s" % child_release)
                self.removeRelease(child_release, recursive=True)
        else:
            # pylint: disable=E1101
            for package in release.packages[:]:
                result = self.removePackage(package, arch=package.arch.name, release=release)
                if result is not True:
                    self.env.log.error("Could not remove package %s from release %s" % (package.name, release.name))
                else:
                    self.env.log.debug("Package %s/%s/%s was removed from release %s" % (package.name, package.version, package.arch.name, release.name))

        if release.distribution.installation_method is not None:
            self.install_method_reg[release.distribution.installation_method].removeRelease(release.name, recursive=recursive)

        result = self.type_reg[release.distribution.type.name].removeRelease(self._session, release, recursive=recursive)
        if result is not None:
            try:
                release.distribution.releases.remove(release)
                self._session.delete(release)
                self._session.commit()
            except:
                self._session.rollback()
                raise
        return result

    @Command(__doc__=N_("Rename a release"))
    def renameRelease(self, source, target):
        """
        renameRelease changes the name from source to target.

        @type source: string
        @param source: source release name

        @type target: string
        @param target: target release name

        @rtype: boolean
        @return: True for success
        """
        result = None

        if isinstance(source, StringTypes):
            release = self._getRelease(source)

        if release is None:
            raise ValueError(N_("Source release {release} not found").format(release=source))
        instance = self._getRelease(target)
        if instance is not None:
            raise ValueError(N_("Release {release} already exists").format(release=target))
        else:
            result = self.type_reg[release.distribution.type.name].renameRelease(self._session, release, target)
        return result

    @Command(__doc__=N_("Replace distribution properties"))
    @NamedArgs("m_hash")
    def setDistribution(self, m_hash=None, distribution=None, arch=None, component=None, mirror_sources=None):
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s was not found", distribution))
                else:
                    distribution = instance

            # Handle architectures
            if not arch:
                arch = []

            # Clean architectures that are not used anymore
            for ar in distribution.architectures:
                if not ar.name in arch:
                    del distribution.architectures[distribution.architectures.index(ar)]

            # Add new architectures
            for ar in arch:
                if isinstance(ar, StringTypes):
                    instance = self._getArchitecture(ar, add=True)
                    if not instance:
                        raise ValueError(N_("Architecture %s was not found", ar))
                    else:
                        ar = instance
                if ar not in distribution.architectures:
                    distribution.architectures.append(ar)

            # Handle components
            if not component:
                component = []

            # Clean components that are not used anymore
            for cp in distribution.components:
                if not cp.name in component:
                    del distribution.components[distribution.components.index(cp)]

            # Add new components
            for cp in component:
                if isinstance(cp, StringTypes):
                    instance = self._getComponent(cp, add=True)
                    if not instance:
                        raise ValueError(N_("Component %s was not found", cp))
                    else:
                        cp = instance
                if cp not in distribution.components:
                    distribution.components.append(cp)

            if mirror_sources:
                distribution.mirror_sources = mirror_sources
        else:
            raise ValueError(N_("Need a distribution to add properties"))
        try:
            self._session.commit()
            result = True
        except:
            self._session.rollback()
            raise
        return result

    @Command(__doc__=N_("Add new properties to a mirrored distribution"))
    @NamedArgs("m_hash")
    def addMirrorProperty(self, m_hash=None, distribution=None, arch=None, component=None, mirror_sources=None):
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s was not found", distribution))
                else:
                    distribution = instance
            if arch:
                if isinstance(arch, StringTypes):
                    instance = self._getArchitecture(arch, add=True)
                    if not instance:
                        raise ValueError(N_("Architecture %s was not found", arch))
                    else:
                        arch = instance
                if arch not in distribution.architectures:
                    distribution.architectures.append(arch)
            if component:
                if isinstance(component, StringTypes):
                    instance = self._getComponent(component, add=True)
                    if not instance:
                        raise ValueError(N_("Component %s was not found", component))
                    else:
                        component = instance
                if component not in distribution.components:
                    distribution.components.append(component)
            if mirror_sources:
                distribution.mirror_sources = mirror_sources
        else:
            raise ValueError(N_("Need a distribution to add properties"))
        try:
            self._session.commit()
            result = True
        except:
            self._session.rollback()
            raise
        return result

    @Command(__doc__=N_("Remove existing properties from a mirrored distribution"))
    @NamedArgs("m_hash")
    def removeMirrorProperty(self, m_hash=None, distribution=None, arch=None, component=None):
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s was not found", distribution))
                else:
                    distribution = instance
            if arch:
                if isinstance(arch, StringTypes):
                    instance = self._getArchitecture(arch)
                    if not instance:
                        raise ValueError(N_("Architecture %s was not found", arch))
                    else:
                        arch = instance
                if arch in distribution.architectures:
                    distribution.architectures.remove(arch)
            if component:
                if isinstance(component, StringTypes):
                    instance = self._getComponent(component)
                    if not instance:
                        raise ValueError(N_("Component %s was not found", component))
                    else:
                        component = instance
                if component in distribution.components:
                    distribution.components.remove(component)
            else:
                raise ValueError(N_("Distribution %s has no releases", distribution.name))
        else:
            raise ValueError(N_("Need a distribution to remove properties"))
        try:
            self._session.commit()
            result = True
        except:
            self._session.rollback()
            raise
        return result

    @Command(__doc__=N_("Update a local mirror"))
    @NamedArgs("m_hash")
    def updateMirror(self, m_hash=None, distribution=None):
        result = None
        if distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s was not found", distribution))
                else:
                    distribution = instance
            if distribution.releases:
                distribution._sync()
                result = True
            else:
                raise ValueError(N_("Distribution %s has no releases", distribution.name))
        else:
            raise ValueError(N_("Need a distribution to update"))
        return result

    def createMirror(self, distribution, release):
        #TODO
        pass

    def removeMirror(self, distribution, release):
        #TODO
        pass

    def addChannel(self, url):
        #TODO
        pass

    def removeChannel(self, id, recursive=None):
        #TODO
        pass

    #TODO: list channels/mirrors

    @Command(__doc__=N_("List packages by various criteria"))
    @NamedArgs("m_hash")
    def getPackages(self, m_hash=None, release=None, arch=None, section=None, custom_filter=None,
        offset=None, limit=None):
        """
        getPackages lists available packages using the specified
        criteria.

        @type release: string/Release
        @param release: Optional release instance or release name

        @type arch: string/Architecture
        @param arch: Optional name or instance of architecture (i.e. 'i386', 'amd64')

        @type section: string/Section
        @param section: Optional name or instance of section (i.e. 'main', 'contrib')

        @type custom_filter: string
        @param filter: #TODO: really a string? if not, is it serializable?

        @type offset: int
        @param offset: Offset to begin with, starting with 0

        type limit: int
        @param limit: Limit result entries

        @rtype: list
        @return: list of package names
        """
        def package_filter(package):
            if arch and not package.arch.name == arch:
                return False
            if section and not package.section.name == section:
                return False
            return True

        result = None
        if arch and isinstance(arch, Architecture):
            arch = arch.name
        if section and isinstance(section, Section):
            section = section.name
        if release and isinstance(release, StringTypes):
            release = self._getRelease(release)
            if release is None:
                return result
            else:
                result = filter(package_filter, release.packages)
        else:
            if custom_filter:
                result = self._session.query(Package.name.like(custom_filter))
            elif arch or section:
                result = self._session.query(Package)
                if arch:
                    result = result.join(Architecture).filter_by(name=arch)
                if section:
                    result = result.join(Section).filter_by(name=section)
            else:
                result = self._session.query(Package).all()
        if limit or offset:
            result = result[offset:][:limit]

        return [package.getInfo() for package in result]

    @Command(__doc__=N_("Get complete package information based on various criteria"))
    @NamedArgs("m_hash")
    def getPackagesInformation(self, m_hash=None, release=None, arch=None, section=None, custom_filter=None,
        offset=None, limit=None):
        """
        Like getPackages, but returns a complete dictionary with package information.

        @type release: string/Release
        @param release: Optional release instance or release name

        @type arch: string/Architecture
        @param arch: Optional name or instance of architecture (i.e. 'i386', 'amd64')

        @type section: string/Section
        @param section: Optional name or instance of section (i.e. 'main', 'contrib')

        @type custom_filter: string
        @param custom_filter: #TODO: really a string? if not, is it serializable?

        @type offset: int
        @param offset: Offset to begin with, starting with 0

        type limit: int
        @param limit: Limit result entries

        @rtype: dict
        @return: #TODO
        """
        pass

    @Command(__doc__=N_("Get single package information"))
    def getPackageInformation(self, release, arch, package):
        """
        getPackageInformation returns a dictionary containing package information.

        @type release: string/Release
        @param release: Optional release instance or release name

        @type arch: string/Architecture
        @param arch: Optional name or instance of architecture (i.e. 'i386', 'amd64')

        @type package: string
        @param package: Package name

        @rtype: dict
        @return: dictionary containing package information
        """
        pass

    @Command(__doc__=N_("Add a package to the selected distribution/release"))
    @NamedArgs("m_hash")
    def addPackage(self, url, m_hash=None, release=None, distribution=None, component=None, updateInventory=True):
        """
        addPackage adds one package to a distribution.

        @type url: string
        @param url: Local or remote path to package file (supported remote protocols: http/https/ftp)

        @type release: string
        @param release: (optional) add package to specified release

        @type distribution: string
        @param distribution: (optional) add package to specified distribution

        @type component: string
        @param component: (optional) override component for package

        @type updateInventory: boolean
        @param updateInventory: rebuild packages list after adding package

        @rtype: boolean
        @return: adding package successfull
        """
        result = None
        download_dir = None
        local_url = None

        if release:
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if instance is not None:
                    release = instance
                else:
                    raise ValueError(N_("Release {release} does not exist!").format(release=release))

        elif distribution:
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(release)
                if instance is not None:
                    distribution = instance
                else:
                    raise ValueError(N_("Distribution {distribution} does not exist!").format(distribution=distribution))
        else:
            raise ValueError(N_("Need either a release or a distribution to add a Package"))

        if url.startswith(('http', 'ftp')):
            download_dir = tempfile.mkdtemp()
            request = urllib2.Request(url)
            try:
                file = urllib2.urlopen(request)
                file_name = url.split('/')[-1]
                local_file = open(download_dir + os.sep + file_name, "w")
                local_file.write(file.read())
                local_file.close()
                local_url = download_dir + os.sep + file_name
            except urllib2.HTTPError, e:
                print "HTTP Error:", e.code, url
            except urllib2.URLError, e:
                print "URL Error:", e.reason, url

        if os.path.exists(local_url):
            # get file extension
            file_ext = local_url.split('.')[-1]
            type_name = None
            if release:
                type_name = release.distribution.type.name
            elif distribution:
                type_name = distribution.type.name
            elif file_ext in self.type_reg:
                type_name = file_ext
            else:
                raise ValueError(N_("Don't know how to handle {url}").format(url=url))

            # Distribution specific method must handle duplicates
            result = self.type_reg[file_ext].addPackage(self._session,
                                                        local_url,
                                                        distribution=distribution,
                                                        release=release,
                                                        component=component,
                                                        origin=url)
        else:
            raise ValueError(N_("Path '{url}' is not readable").format(url=url))

        if result is not None:
            result.origin = url
            try:
                self._session.commit()
                if updateInventory:
                    self._updateInventory(release=release, distribution=distribution)
            except:
                self._session.rollback()

        if download_dir:
            try:
                shutil.rmtree(download_dir)
            except:
                raise

        return result != None

    @Command(__doc__=N_("Remove a package from the selected release"))
    @NamedArgs("m_hash")
    def removePackage(self, package, m_hash=None, arch=None, release=None, distribution=None):
        """
        removePackage removes a package from a release.

        @type package: string
        @param package: package name

        @type release: string
        @param release: name of the release

        @rtype: boolean
        @return: adding package successfull
        """
        result = False
        package_name = package

        if isinstance(package, StringTypes):
            package = self._getPackage(package, arch=arch)

        if package is not None:
            package_name = package.name
            result = self.type_reg[package.type.name].removePackage(self._session, package, arch=arch, release=release, distribution=distribution)
            if result:
                try:
                    self._session.commit()
                except:
                    self.env.log.error("Commiting changes when deleting package %s failed!" % package_name)
                    self._session.rollback()
                    result = False
                    raise
        else:
            raise ValueError(N_("Package {package} not found!").format(package=package_name))
        return result

    def addKeys(self, keys):
        result = False
        if not self._repository.keyring:
            self._repository.keyring = RepositoryKeyring(data=keys)
            work_dir = self._getGPGEnvironment()
            gpg = gnupg.GPG(gnupghome=work_dir)
            for key in gpg.list_keys(True):
                if key['type'] == "sec":
                    self._repository.keyring.name = key['fingerprint']
                    break
            shutil.rmtree(work_dir)
            result = True
        else:
            work_dir = self._getGPGEnvironment()
            gpg = gnupg.GPG(gnupghome=work_dir)
            # pylint: disable=E1101
            import_result = gpg.import_keys(keys)
            if import_result.count > 0:
                result = True
            shutil.rmtree(work_dir)
        return result

    def removeKey(self, key_id):
        result = None
        work_dir = self._getGPGEnvironment()
        gpg = gnupg.GPG(gnupghome=work_dir)
        fp = None
        for key in gpg.list_keys(True):
            if key['keyid'] == key_id or key['fingerprint'] == key_id:
                fp = key['fingerprint']
                break
        if fp is not None:
            if gpg.delete_keys(fp, secret=True).status == "ok":
                self._repository.keyring.data = gpg.list_keys(True)
                if self._repository.keyring.name == fp:
                    self._repository.keyring.name = None
                result = True
        shutil.rmtree(work_dir)
        return result

    def listKeys(self):
        result = None
        work_dir = self._getGPGEnvironment()
        gpg = gnupg.GPG(gnupghome=work_dir)
        result = gpg.list_keys(True)
        shutil.rmtree(work_dir)
        return result

    @Command(__doc__=N_("Returns a list of items of item_type (if given) for the specified release - or all."))
    @NamedArgs("m_hash")
    def listConfigItems(self, release, m_hash=None, item_type=None, path=None, children=None):
        result = None
        if isinstance(release, StringTypes):
            instance = self._getRelease(release)
            if instance is None:
                raise ValueError("Unknown release %s" % release)
            else:
                release = instance
        elif isinstance(release, DictType):
            pass
        elif not isinstance(release, Release):
            raise ValueError(N_("Argument release must either be a String or a Release"))
        if release.distribution.installation_method is None:
            raise ValueError("Release %s has no installation method!" % release.name)
        elif release.distribution.installation_method not in self.install_method_reg:
            raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method, release.name))
        else:
            result = self.install_method_reg[release.distribution.installation_method].listItems(release.name, item_type=item_type, path=path, children=children)
        return result

    @Command(__doc__=N_("Set the data for the specified item"))
    def setConfigItem(self, release, path, item_type, data):
        result = None
        if isinstance(release, StringTypes):
            instance = self._getRelease(release)
            if instance is None:
                raise ValueError("Unknown release %s" % release)
            else:
                release = instance
        if release.distribution.installation_method is None:
            raise ValueError("Release %s has no installation method!" % release.name)
        elif release.distribution.installation_method not in self.install_method_reg:
            raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method, release.name))
        else:
            result = self.install_method_reg[release.distribution.installation_method].setItem(release.name, path, item_type, data)
        return result

    @Command(__doc__=N_("Remove the specified item and it's children"))
    def removeConfigItem(self, release, path, children=None):
        result = None
        if isinstance(release, StringTypes):
            instance = self._getRelease(release)
            if instance is None:
                raise ValueError("Unknown release %s" % release)
            else:
                release = instance
        if release.distribution.installation_method is None:
            raise ValueError("Release %s has no installation method!" % release.name)
        elif release.distribution.installation_method not in self.install_method_reg:
            raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method,
                        release.name))
        else:
            result = self.install_method_reg[release.distribution.installation_method].removeItem(release.name, path, children)
        return result

    @Command(__doc__=N_("Return the data of specified item"))
    def getConfigItem(self, release, path):
        result = None
        if isinstance(release, StringTypes):
            instance = self._getRelease(release)
            if instance is None:
                raise ValueError("Unknown release %s" % release)
            else:
                release = instance
        if release.distribution.installation_method is None:
            raise ValueError("Release %s has no installation method!" % release.name)
        elif release.distribution.installation_method not in self.install_method_reg:
            raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method,
                        release.name))
        else:
            result = self.install_method_reg[release.distribution.installation_method].getItem(release.name, path)
        return result

    @Command(__doc__=N_("Get supported system locales"))
    def getSystemLocales(self):
        return locale_map

    @Command(__doc__=N_("Get supported keyboard models"))
    def getKeyboardModels(self):
        return self.keyboardModels

    @Command(__doc__=N_("Get supported time zones"))
    def getTimezones(self):
        return pytz.all_timezones

    @Command(__doc__=N_("Get kernel packages for the specified release"))
    def getKernelPackages(self, release):
        distribution = self._getDistribution(release.split('/')[0])
        if distribution:
            release = self._getRelease(release.split('/', 1)[1])
        else:
            return []

        repo_type = distribution.type.name
        pname = self.type_reg[repo_type].getKernelPackageFilter()
        return self.getPackages(release=release.name, custom_filter={'name': pname})

    @Command(__doc__=N_("Completely remove device's installation parameters"))
    def removeBaseInstallParameters(self, device_uuid):
        data = load_system(device_uuid)
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        inst_m = self.base_install_method_reg[method]
        return inst_m.removeBaseInstallParameters(device_uuid, data)

    @Command(__doc__=N_("Get device's installation method"))
    def systemGetBaseInstallMethod(self, device_uuid, data=None):
        # Load system
        if not data:
            data = load_system(device_uuid)

        if not "installTemplateDN" in data:
            raise ValueError("device with UUID '%s' has no install template assigned" % device_uuid)

        # Inspect template for install method
        if not "installMethod" in data:
            return None

        return data["installMethod"].lower()

    @Command(__doc__=N_("Get device's filled install template"))
    def systemGetTemplate(self, device_uuid):
        """ Evaulate template for system with device_uuid 'device_uuid' """
        data = load_system(device_uuid)
        method = self.systemGetBaseInstallMethod(device_uuid, data)

        # Use the method described by "method" and pass evaluated data
        if not method in self.base_install_method_reg:
            raise ValueError("device with UUID '%s' has an unknown installation method assigned" % device_uuid)

        inst_m = self.base_install_method_reg[method]
        return inst_m.getTemplate(data)

    @Command(__doc__=N_("Get device's configuration method"))
    def systemGetConfigMethod(self, device_uuid, data=None):
        if not data:
            data = load_system(device_uuid)

        if not "configMethod" in data:
            return None

        return data["configMethod"].lower()

    @Command(__doc__=N_("Get device's boot string"))
    def systemGetBootParams(self, device_uuid, mac=None):
        params = []
        data = load_system(device_uuid, mac)
        device_uuid = data['deviceUUID'][0]
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        c_method = self.systemGetConfigMethod(device_uuid, data)

        # Use the method described by "method" and pass evaluated data
        if not method in self.base_install_method_reg:
            raise ValueError("device with UUID '%s' has an unknown installation method assigned" % device_uuid)

        # Load base install parameters
        inst_m = self.base_install_method_reg[method]
        params += inst_m.getBootParams(device_uuid)

        # Load config parameters
        if c_method:
            conf_m = self.install_method_reg[c_method]()
            params += conf_m.getBootParams(device_uuid)

        # Check device status before returning anything
        if not "deviceStatus" in data or "A" not in data["deviceStatus"][0]:
            return None

        # Append device key if available
        if "deviceKey" in data:
            params.append("svc_key=%s" % data["deviceKey"][0])

        #TODO: for non DNS/zeroconf setups, it might be a good idea to
        #      send a connection URI, too

        return " ".join(params)

    @Command(__doc__=N_("Get device's boot string"))
    def systemGetBootConfiguration(self, device_uuid, mac=None):
        data = load_system(device_uuid, mac)
        device_uuid = data['deviceUUID'][0]
        method = self.systemGetBaseInstallMethod(device_uuid, data)

        # Use the method described by "method" and pass evaluated data
        if not method in self.base_install_method_reg:
            raise ValueError("device with UUID '%s' has an unknown installation method assigned" % device_uuid)

        # Get boot configuration from installation method
        inst_m = self.base_install_method_reg[method]
        return inst_m.getBootConfiguration(device_uuid)

    @Command(__doc__=N_("Get device's base install parameters"))
    def systemGetBaseInstallParameters(self, device_uuid):
        data = load_system(device_uuid)
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        inst_m = self.base_install_method_reg[method]
        return inst_m.getBaseInstallParameters(device_uuid, data)

    @Command(__doc__=N_("Set device's base install parameters"))
    def systemSetBaseInstallParameters(self, device_uuid, data):
        sys_data = load_system(device_uuid)
        method = self.systemGetBaseInstallMethod(device_uuid, sys_data)
        inst_m = self.base_install_method_reg[method]
        return inst_m.setBaseInstallParameters(device_uuid, data, sys_data)

#---------------------------------------------------------------------------------------------#

    def _getArchitecture(self, name, add=False):
        result = None
        try:
            result = self._session.query(Architecture).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Architecture(name)
                self._session.add(result)
        return result

    def _getSection(self, name, add=False):
        result = None
        try:
            result = self._session.query(Section).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Section(name)
                self._session.add(result)
        return result

    def _getComponent(self, name, add=False):
        result = None
        try:
            result = self._session.query(Component).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Component(name)
                self._session.add(result)
        return result

    def _getFile(self, url, add=False):
        result = None
        try:
            result = self._session.query(File).filter_by(name=os.path.basename(url)).one()
        except NoResultFound:
            if add:
                result = File(name=os.path.basename(url))
                if os.path.exists(url):
                    infile = open(url, 'rb')
                    content = infile.read()
                    infile.close()
                    m = hashlib.md5()
                    m.update(content)
                    result.md5sum = m.hexdigest()
                    result.size = os.path.getsize(url)
                self._session.add(result)
        return result

    def _getType(self, name, add=False):
        result = None
        try:
            result = self._session.query(Type).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Type(name)
                self._session.add(result)
        return result

    def _getDistribution(self, name):
        result = None
        try:
            result = self._session.query(Distribution).filter_by(name=name).one()
        except NoResultFound:
            pass
        return result

    def _getRelease(self, name):
        result = None
        try:
            result = self._session.query(Release).filter_by(name=name).one()
        except NoResultFound:
            pass
        return result

    def _getRepository(self, name=None, path=None, add=False):
        result = None

        try:
            result = self._session.query(Repository)
            if name:
                result = result.filter_by(name=name)
            elif path:
                result = result.filter_by(path=path)
            result = result.one()
        except NoResultFound:
            if add:
                result = Repository(name=name, path=path)
                self._session.add(result)
        return result

    def _getPackage(self, name, arch=None):
        try:
            result = self._session.query(Package).filter_by(name=name)
            if arch:
                if isinstance(arch, StringTypes):
                    arch = self._getArchitecture(arch)
                result = result.filter_by(arch=arch)
            result = result.one()
        except:
            raise
        return result

    def _updateInventory(self, distribution=None, release=None):
        """
        TODO
        @type distribution: string/Distribution
        @param distribution: distribution name/instance

        @type release: string/Release
        @param release: release name/instance

        @rtype: boolean
        @return: True for success
        """
        result = None
        if release:
            if isinstance(release, StringTypes):
                release = self._getRelease(release)
            result = self.type_reg[release.distribution.type.name]._updateInventory(self._session, release=release)
        elif distribution:
            if isinstance(distribution, StringTypes):
                distribution = self._getDistribution(distribution)
            result = self.type_reg[distribution.type.name]._updateInventory(self._session, distribution=distribution)
        try:
            self._session.commit()
        except:
            self._session.rollback()
        return result

    def _getConfigItem(self, name, item_type, release=None, add=False):
        result = None
        try:
            result = self._session.query(ConfigItem)
            if name:
                result = result.filter_by(name=name)
            if item_type:
                result = result.filter_by(item_type=item_type)
            if release:
                result = result.join(ConfigItemReleases).join(Release).filter_by(name=release)
            result = result.one()
        except NoResultFound:
            result = ConfigItem(name=name, item_type=item_type)
            self._session.add(result)
        return result

    def _replaceConfigItems(self, release, items):
        result = None

        if isinstance(release, StringTypes):
            release = self._getRelease(release)

        # Iterate over DB Items, delete orphans
        for item_name, item_type in self.listItems(release).iteritems():
            if self._getConfigItem(item_name, item_type, release=release):
                if item_name not in items:
                    db_instance = self._getConfigItem(item_name, item_type, release=release)
                    self._session.merge(db_instance)
                    release.config_items.remove(db_instance)
                    self._session.delete(db_instance)

        # Iterate over FS scan, add missing items
        for item_name, item_type in items.iteritems():
            if not self._getConfigItem(item_name, item_type, release=release):
                db_instance = self._getConfigItem(item_name, item_type, release=release, add=True)
                release.config_items.append(db_instance)
                self._session.add(db_instance)

        try:
            self._session.commit()
        except:
            self._session.rollback()
            raise

        return result

    def listItems(self, release, item_type=None, path=None, children=None):
        """
        Returns a list of items of item_type (if given) for
        the specified release - or all.

        @type release: string
        @param release: release path

        @type item_type: string
        @param item_type: type of item to list, None for all

        @type path: string
        @param path: path to list items on

        @rtype: dict
        @return: dictionary of name/item_type pairs
        """
        res = {}
        first = False

        if not children:
            children = self._getRelease(release).config_items
            first = True

        def filter_items(item):
            path_match = True
            if path:
                path_match = item.name.startswith(path + "/")

            if item_type:
                return path_match and (item_type == item.item_type)

            return path_match

        items = filter(filter_items, children)
        res = dict((i.getPath(), i.item_type) for i in items)

        # Iterate for items with children
        for item in filter(lambda i: i.children, items):
            res.update(self.listItems(release, item_type, path, item.children))

        return res

    #============================================
    # return the session to be used in the tests.
    #============================================
    def getSession(self):
        return self._session

    def _getGPGEnvironment(self):
        result = None
        work_dir = tempfile.mkdtemp()
        gpg = gnupg.GPG(gnupghome=work_dir)
        if not self._repository.keyring:
            #TODO: Config options for key type and length?
            key_type = "RSA"
            key_length = 1024
            self.env.log.debug("Generating GPG Key, type %s and length %s Bit" % (key_type, key_length))
            input_data = gpg.gen_key_input(key_type=key_type, key_length=key_length)
            key = gpg.gen_key(input_data)
            self._repository.keyring = RepositoryKeyring(name=key.fingerprint, data=gpg.export_keys(key, True))
            self._session.commit()
        else:
            gpg.import_keys(self._repository.keyring.data)
        result = work_dir
        return result


class NotFoundException(Exception):
    pass
