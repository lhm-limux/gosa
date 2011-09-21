# -*- coding: utf-8 -*-
"""
The *LibinstManager* proxies the complete repository, base installation and
config management process to the target plugins. It is the abstraction layer
to be used from your frontend - shell, GUI or whatever you tend to use.

----------
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
import platform
import datetime
import logging

from base64 import encodestring as encode
from types import StringTypes, DictType, ListType
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, scoped_session

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
from libinst.utils import load_system

from gosa.common import Environment
from gosa.common.components.command import Command
from gosa.agent.ldap_utils import LDAPHandler
from gosa.common.components import Plugin
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

class LibinstManager(Plugin):
    """
    Manage repositories, base install and configuration of clients.
    """
    _target_ = 'libinst'
    recipeRecursionDepth = 3
    template_map = {"cn": "name",
        "description": "description",
        "installMethod": "method",
        "templateData": "data"}

    def __init__(self):
        env = Environment.getInstance()
        self.env = env
        self.log = logging.getLogger(__name__)
        engine = env.getDatabaseEngine("repository")
        Session = scoped_session(sessionmaker(autoflush=True, bind=engine))
        self.path = env.config.get('repository.path')
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except:
                raise

        self.hostname = platform.node()
        #self.path = self.hostname+":"+self.path

        # Load all repository handlers
        self.type_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.repository"):
            module = entry.load()
            self.log.info("repository handler %s included" % module.__name__)
            for module_type in module.getRepositoryTypes():
                self.type_reg[module_type] = module(self)

        # Load all installation methods
        self.install_method_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.methods"):
            module = entry.load()
            self.log.info("installation method %s included " % module.__name__)
            self.install_method_reg[module.getInfo()['name'].lower()] = module(self)

        # Load all base installation methods
        self.base_install_method_reg = {}
        for entry in pkg_resources.iter_entry_points("libinst.base_methods"):
            module = entry.load()
            self.log.info("base installation method %s included " % module.__name__)
            self.base_install_method_reg[module.getInfo()['name'].lower()] = module()

        # Purge DB if wanted
        db_purge = env.config.get('repository.db_purge')
        if db_purge == "True":
            self.initializeDatabase(engine)

        # Initialize Repository instance
        self._getRepository(path=self.path, add=True)

        # Load keyboard models
        self.keyboardModels = KeyboardModels().get_models()

    def initializeDatabase(self, engine):
        """
        Initialize the database by dropping everything and recreating the
        table schema.
        """
        a = Base()
        # pylint: disable=E1101
        a.metadata.drop_all(engine)
        # pylint: disable=E1101
        a.metadata.create_all(engine)

    @Command(__help__=N_("List the available base install methods"))
    def getSupportedBaseInstallMethods(self):
        """
        List the registered :class:`libinst.methods.BaseInstallMethod` methods.
        Registration works by specifying a setuptools ``[libinst.base_methods]``
        entrypoint.

        Example:

        >>> proxy.getSupportedBaseInstallMethods()
        {'preseed': {'title': 'Debian preseed installation method',
        'repositories': ['deb'], 'methods': ['puppet'], 'name': 'Preseed',
        'description': 'Base installation using the debian installer'}}

        The returned dictionary has the install method name as the key and
        these information keys:

        ============= =======================================
        Key           Description
        ============= =======================================
        name          Symbolic name of the method
        title         Short description
        description   Long description
        repositories  List of supported repositories
        methods       List of supported configuration methods
        ============= =======================================

        ``Return:`` dictionary
        """
        res = {}
        for name, method in self.base_install_method_reg.items():
            res[name] = method.getInfo()

        return res

    @Command(__help__=N_("List the available installation methods"))
    def getSupportedInstallMethods(self):
        """
        List the registered :class:`libinst.methods.InstallMethod` methods.
        Registration works by specifying a setuptools ``[libinst.methods]``
        entrypoint.

        Example:

        >>> proxy.getSupportedInstallMethods()
        {'puppet': ....}

        The returned dictionary has the install method name as the key and
        these information keys:

        ============= =======================================
        Key           Description
        ============= =======================================
        name          Display name of the method
        description   Long description
        title         Short description
        items         Symbolic name of the method
        repositories  List of supported repositories
        ============= =======================================

        The items are a dictionary by themselves, where the key is the item name:

        ============= =======================================
        Key           Description
        ============= =======================================
        name          Display name of the item
        description   Long description of the item
        container     List of sub-items this item can contain
        options       Description of supported item options
        ============= =======================================

        The item options are a dictionary by themselves, where the key is the option name:

        ============= =========================================
        Key           Description
        ============= =========================================
        display       Display label
        description   Long description
        default       Default value
        required      Flag if option is mandatory
        value         Current value (if applicable)
        type          Option type (file, string, bool, integer)
        ============= =========================================

        ``Return:`` dictionary
        """
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

    @Command(__help__=N_("List the available repository types for this host"))
    def getSupportedRepositoryTypes(self):
        """
        List registered :class:`libinst.interface.DistributionHandler` objects.
        Registration works by specifying a setuptools ``[libinst.repository]``
        entrypoint.

        >>> proxy.getSupportedRepositoryTypes()
        ['deb', 'udeb', 'dsc']

        ``Return:`` list
        """
        #TODO: what about descriptions like in getRepositoryTypes?
        return self.type_reg.keys()

    @Command(__help__=N_("List used repository types"))
    def getRepositoryTypes(self):
        """
        List used repository types from the database including their description:

        >>> proxy.getRepositoryTypes()
        ['deb': '', 'dsc': '']

        ``Return:`` Dictionary pairing name with description
        """
        result = None
        session = None
        try:
            session = self.getSession()
            result = dict([(type.name, type.description) for type in session.query(Type).all()])
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Get the external repository URL for the given release"))
    def getMirrorURL(self, release):
        """
        Return the URL to an external repository for the provided release.

        >>> proxy.getMirrorURL("squeeze")
        'http://mirror.example.net/debian/squeeze'

        ========= ============
        Parameter Description
        ========= ============
        release   Target release to query for mirror
        ========= ============

        ``Return:`` mirror URL
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if not self.env.config.get('repository.http_base_url'):
                raise ValueError(N_("Option 'http_base_url' in section 'repository' is not configured!"))
            distribution = self._getDistribution(release.split('/')[0])
            if distribution:
                distribution = session.merge(distribution)
                release = release.split('/', 1)[1]
            if not self._getRelease(release):
                raise ValueError(N_("Release {release} was not found!").format(release=release))
            else:
                release = self._getRelease(release)
                release = session.merge(release)
            result = self.env.config.get('repository.http_base_url')
            if not result.endswith('/'):
                result += '/'
            if distribution is not None:
                result += distribution.name + '/'
            else:
                result += release.distribution.name + '/'
            result += release.name
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("List available distributions"))
    def getDistributions(self):
        """
        Return a list of distribution descriptions from the database.

        >>> proxy.getDistributions()
        [{'origin': None, 'installation_method': 'puppet', 'last_updated': None, 'name': 'debian', 'releases': [{'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}, {'origin': None, 'codename': None, 'name': 'squeeze/1.0', 'parent': {'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}}], 'sections': [{'name': 'sound', 'description': None}, {'name': 'kernel', 'description': None}, {'name': 'debug', 'description': None}], 'type': {'name': 'deb', 'description': ''}, 'debian_volatile': None, 'debian_security': None, 'architectures': [{'name': 'i386', 'description': None}, {'name': 'amd64', 'description': None}, {'name': 'source', 'description': None}], 'components': [{'name': 'main', 'description': None}], 'path': '/srv/repository/data/debian', 'mirror_sources': False, 'managed': True}]

        Every list element is a dictionary with these keys:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Distribution name
        origin              Filter by mirror origin
        installation_method Method to be used for this distribution
        last_updated        Timestamp of last update
        releases            List of releases the use this distribution as parent
        sections            List of sections in this distribution
        components          List of components in this distribution
        architectures       List of supported architectures
        path                Local mirror path
        mirror_sources      Flag whether to mirror sources or not
        managed             Flag whether mirrored distributions are listed or not
        =================== ====================================================

        The list of releases contains descriptive dicts, too:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Name of the release
        codename            Codename of the release
        parent              Name of the parent release
        origin              Name of the origin if release belongs to a mirror distribution
        =================== ====================================================

        In the debian way of packaging, sections are something like *sound*, *net*, etc.
        The list of sections contains descriptive dicts, too:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Name of the section
        description         Descriptive text
        =================== ====================================================

        In the debian way of packaging, components are something like *main*, *contrib*, etc.
        The list of components contains descriptive dicts, too:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Name of the component
        description         Descriptive text
        =================== ====================================================

        The list of architectures contains descriptive dicts, too:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Name of the architecture
        description         Descriptive text
        =================== ====================================================

        ``Return:`` list of dicts
        """
        result = None
        repository = None
        session = None

        try:
            session = self.getSession()
            repository = self._getRepository(path=self.path)
            session.add(repository)
            if repository.distributions:
                result = [distribution.getInfo() for distribution in repository.distributions]
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("Return available information for the given distribution"))
    def getDistribution(self, distribution=None):
        """
        Return information about the named distribution.

        ========= ============
        Parameter Description
        ========= ============
        m_hash    Dictionary with distribution name
        ========= ============

        For information about the returned dict, please see
        :meth:`libinst.manage.LibinstManager.getDistributions`.

        Example:

        >>> proxy.getDistribution({'distribution': 'debian'})
        {'origin': None, 'installation_method': 'puppet', 'last_updated': None, 'name': 'debian', 'releases': [{'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}, {'origin': None, 'codename': None, 'name': 'squeeze/1.0', 'parent': {'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}}], 'sections': [{'name': 'sound', 'description': None}, {'name': 'kernel', 'description': None}, {'name': 'debug', 'description': None}], 'type': {'name': 'deb', 'description': ''}, 'debian_volatile': None, 'debian_security': None, 'architectures': [{'name': 'i386', 'description': None}, {'name': 'amd64', 'description': None}, {'name': 'source', 'description': None}], 'components': [{'name': 'main', 'description': None}], 'path': '/srv/repository/data/debian', 'mirror_sources': False, 'managed': True}

        ``Return:`` dictionary describing the distribution
        """
        #TODO: reason for m_hash in signature?
        result = None
        session = None

        if not distribution:
            raise ValueError(N_("Distribution parameter is mandatory"))

        try:
            session = self.getSession()
            if isinstance(distribution, StringTypes):
                result = self._getDistribution(distribution)
            if result is not None:
                result = session.merge(result)
                result = result.getInfo()
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("List available releases for the given distribution"))
    def getReleases(self, distribution=None):
        """
        List releases by distribution or all.

        Example:

        >>> proxy.getReleases({'distribution': 'debian'})
        [{'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}, {'origin': None, 'codename': None, 'name': 'squeeze/1.0', 'parent': {'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}}]

        A release dict contains the following keys:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Name of the release
        codename            Codename of the release
        origin              Origin of the release
        parent              Name of the parent release
        =================== ====================================================

        ``Return:`` list of dicts
        """
        #TODO: what's the reason for m_hash here?
        result = None
        session = None

        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(distribution)
                    if not instance:
                        raise ValueError(N_("Distribution %s not found" % distribution))
                    else:
                        distribution = instance
                    distribution = session.merge(distribution)
                result = distribution.releases
            else:
                result = session.query(Release).all()
            result = [release.getInfo() for release in result]
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("Return available information for the given release"))
    def getRelease(self, release=None):
        """
        Returns information about the privided release.

        ========= ============
        Parameter Description
        ========= ============
        m_hash    Dictionary with release name
        ========= ============

        Example:

        >>> proxy.getRelease({'release': 'squeeze/1.0'})
        {'origin': None, 'codename': None, 'name': 'squeeze/1.0', 'parent': {'origin': None, 'codename': None, 'name': 'squeeze', 'parent': None}}

        The resulting dictionary contains this information:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Release name
        codename            Code name
        origin              URL of the origin
        parent              Parent release information
        =================== ====================================================

        ``Return:`` dict with information
        """
        #TODO: reason for m_hash?
        result = None
        session = None

        if not release:
            raise ValueError(N_("Release parameter is mandatory"))

        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                result = self._getRelease(release)
            if result is not None:
                result = session.merge(result)
                result = result.getInfo()
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("List available architectures for the given distribution"))
    def getArchitectures(self, distribution=None, release=None):
        """
        List available architectures per release, distribution or global.

        ========= ============
        Parameter Description
        ========= ============
        m_hash    Dictionary with release name or distribution name
        ========= ============

        Example:

        >>> proxy.getArchitectures({'release': 'squeeze/1.0'})
        [{'name': 'amd64', 'description': None}]

        The resulting dictionary contains this information:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Release name
        description         Description
        =================== ====================================================

        ``Return:`` dict describing the architectures
        """
        #TODO: reason for m_hash?
        result = None
        session = None

        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    distribution = self._getDistribution(distribution)
                distribution = session.merge(distribution)
                result = session.query(Distribution).filter_by(name=distribution.name).one().architectures
            elif release:
                if isinstance(release, StringTypes):
                    release = self._getRelease(release)
                release = session.merge(release)
                result = set()
                for package in release.packages:
                    result.add(package.arch)
                result = list(result)
            else:
                result = session.query(Architecture).all()
            result = [architecture.getInfo() for architecture in result]
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("List available sections for the given distribution"))
    def getSections(self, distribution=None, release=None):
        """
        List available sections per release, distribution or global.

        ========= ============
        Parameter Description
        ========= ============
        m_hash    Dictionary with release name or distribution name
        ========= ============

        Example:

        >>> proxy.getSections({'release': 'squeeze/1.0'})
        [{'name': 'kernel', 'description': None}, {'name': 'sound', 'description': None}]

        The resulting dictionary contains this information:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Release name
        description         Description
        =================== ====================================================

        ``Return:`` dict describing the sections
        """
        #TODO: reason for m_hash?
        result = None
        session = None
        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    distribution = self._getDistribution(distribution)
                distribution = session.merge(distribution)
                result = session.query(Distribution).filter_by(name=distribution.name).one().sections
            elif release:
                if isinstance(release, StringTypes):
                    release = self._getRelease(release)
                release = session.merge(release)
                result = set()
                for package in release.packages:
                    result.add(package.section)
                result = list(result)
            else:
                result = session.query(Section).all()
            result = [release.getInfo() for release in result]
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Create a new distribution based on type, mirror and installation method"))
    def createDistribution(self, name, type, install_method=None, mirror=None):
        """
        Create a new distribution based on type, mirror and installation method. This
        is the first step to be done before creating releases - because releases depend
        on distributions.

        =============== ============
        Parameter       Description
        =============== ============
        name            The distribution name
        type            Repository type
        install_method  Method to be used for this distribution
        mirror          Optional source for this distribution
        =============== ============

        Example:

        >>> proxy.createDistribution('debian', 'deb',
        ...       {'install_method': 'puppet', 'mirror': 'http://ftp.de.debian.org/debian'})
        >>> proxy.updateMirror(distribution="debian", components=["main"], sections=["shells"])
        >>> proxy.createRelease("debian", "squeeze")

        ``Return:`` True on success
        """
        result = None
        session = None

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
            try:
                session = self.getSession()
                if isinstance(type, StringTypes):
                    type = self._getType(type, add=True)
                session.add(type)
                if type is not None and type.name in self.type_reg:
                    result = self.type_reg[type.name].createDistribution(session, name, mirror=mirror)
                    if result is not None:
                        session.add(result)
                        result.type = type
                        result.installation_method = install_method
                        repository = self._getRepository(path=self.path)
                        session.add(repository)
                        repository.distributions.append(result)
                        result.repository._initDirs()
                else:
                    raise ValueError("Name and Type are both needed for creating a distribution!")
                session.commit()
            except:
                self.log.error("Problem creating distribution %s" % name)
                session.rollback()
                raise
            finally:
                session.close()
        else:
            raise ValueError(N_("Distribution {distribution} already exists!").format(distribution=name))

        return result != None

    @Command(__help__=N_("Remove selected distribution from the repository"))
    def removeDistribution(self, distribution, recursive=False):
        """
        Remove an existing distribution. It checks the dependencies and will
        not remove a parent distribution until the recursive parameter is specified.

        =============== ============
        Parameter       Description
        =============== ============
        distribution    The distribution name
        recursive       Remove all release children, too
        =============== ============

        ``Return:`` True on success
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if not instance:
                    raise ValueError(N_("Distribution %s not found", distribution))
                else:
                    distribution = instance
            distribution = session.merge(distribution)

            if distribution.releases and recursive is not True:
                raise ValueError(N_("Distribution {distribution} contains releases. Need to set recursive or remove all releases to allow removal!").format(distribution=distribution.name))
            else:
                for release in distribution.releases[:]:
                    # We only remove top-level releases
                    if not '/' in release.name:
                        self.log.debug("Removing release %s/%s" % (distribution.name,  release.name))
                        self.removeRelease(release, recursive=recursive)
                session.expire(distribution)

            result = self.type_reg[distribution.type.name].removeDistribution(session, distribution, recursive=recursive)
            if result is not None:
                session.commit()
                distribution.repository.distributions.remove(distribution)
                session.delete(distribution)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result != None

    @Command(__help__=N_("Create a new release belonging to distribution"))
    def createRelease(self, distribution, name):
        """
        Create a new release belonging to a distribution. It
        can optionally have a parent release. Parent releases are specified
        using the name field: i.e. name = 'lenny/5.0.4'

        =============== ======================
        Parameter       Description
        =============== ======================
        distribution    The distribution name
        name            The release name
        =============== ======================

        An usage example can be found at :meth:`libinst.manage.LibinstManger.createDistribution`.

        ``Return:`` True on success
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if isinstance(distribution, StringTypes):
                instance = self._getDistribution(distribution)
                if instance:
                    distribution = instance
                else:
                    raise ValueError(N_("Distribution {distribution} does not exist!").format(distribution=distribution))
            distribution = session.merge(distribution)

            if '/' in name and not self._getRelease(name.rsplit('/', 1)[0]):
                raise ValueError(N_("Parent release {release} not found!").format(release=name.rsplit('/', 1)[0]))

            if not self._getRelease(name):
                p = re.compile(ALLOWED_CHARS_RELEASE)
                if not p.match(name):
                    raise ValueError(N_("Release name {release} contains invalid characters!").format(release=name))
                if name == "master":
                    raise ValueError(N_("master is a reserved keyword!"))

                result = self.type_reg[distribution.type.name].createRelease(session, distribution, name)
                if result is not None:
                    session.add(result)
                    distribution.releases.append(result)
                    if result.parent is not None:
                        for package in result.parent.packages[:]:
                            result.packages.append(package)
                    session.commit()
                    distribution.repository._initDirs()
                    if result.distribution.installation_method is not None:
                        self.install_method_reg[result.distribution.installation_method].createRelease(result.name, result.parent)
            else:
                raise ValueError(N_("Release {release} already exists!").format(release=name))
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result != None

    @Command(__help__=N_("Remove a release"))
    def removeRelease(self, release, recursive=False):
        """
        Remove an existing release. It checks the dependencies and will
        not remove a parent release until the recursive parameter is specified.

        =============== ============
        Parameter       Description
        =============== ============
        release         The release name
        recursive       Remove all release children, too
        =============== ============

        Example:

        >>> proxy.removeRelease(release="squeeze")

        ``Return:`` True on success
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if not instance:
                    raise ValueError(N_("Release %s not found" % release))
                else:
                    release = instance
            release = session.merge(release)
            if release.children and recursive is not True:
                raise ValueError("Won't remove a parent release without being recursived!")
            elif release.children and recursive is True:
                for child_release in release.children[:]:
                    self.log.debug("Removing child release %s" % child_release)
                    self.removeRelease(child_release, recursive=True)
                session.expire(release)
            else:
                # pylint: disable-msg=E1101
                for package in release.packages[:]:
                    result = self.removePackage(package, arch=package.arch.name, release=release)
                    if result is not True:
                        self.log.error("Could not remove package %s from release %s" % (package.name, release.name))
                    else:
                        self.log.debug("Package %s/%s/%s was removed from release %s" % (package.name, package.version, package.arch.name, release.name))
                session.expire(release)

            if release.distribution.installation_method is not None:
                self.install_method_reg[release.distribution.installation_method].removeRelease(release.name, recursive=recursive)
                session.expire(release)

            self.log.debug("Removing release %s" % release.name)
            result = self.type_reg[release.distribution.type.name].removeRelease(session, release.name, recursive=recursive)
            if result is not None:
                session.commit()
                release.distribution.releases.remove(release)
                session.delete(release)
                session.commit()
                self.log.info("Removed release %s" % release.name)
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result != None

    @Command(__help__=N_("Rename a release"))
    def renameRelease(self, source, target):
        """
        renameRelease changes the name from source to target.

        =============== ============
        Parameter       Description
        =============== ============
        source          Source release name
        target          Target release name
        =============== ============

        Example:

        >>> proxy.renameRelease("squeeze", "wheezy")

        ``Return:`` True on success
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if isinstance(source, StringTypes):
                release = self._getRelease(source)
            if release is None:
                raise ValueError(N_("Source release {release} not found").format(release=source))
            release = session.merge(release)
            instance = self._getRelease(target)
            if instance is not None:
                raise ValueError(N_("Release {release} already exists").format(release=target))
            else:
                result = self.type_reg[release.distribution.type.name].renameRelease(session, release, target)
                session.commit()
        except ValueError:
            raise
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Replace distribution properties"))
    def setDistribution(self, distribution=None, arch=None, component=None, mirror_sources=None):
        """
        Modify properties of an existing distribution.

        =============== ============
        Parameter       Description
        =============== ============
        distribution    The distribution name
        arch            List of architectures
        component       List of components
        mirror_sources  Flag to mirror sources
        =============== ============

        Example:

        >>> proxy..setDistribution(
        ... {
        ...     'component': [],
        ...     'distribution': 'debian',
        ...     'arch': [],
        ...     'mirror_sources': False
        ... })

        ``Return:`` True on success
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(distribution)
                    if not instance:
                        raise ValueError(N_("Distribution %s was not found", distribution))
                    else:
                        distribution = instance
                distribution = session.merge(distribution)

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
                    ar = session.merge(ar)
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
                    cp = session.merge(cp)
                    if cp not in distribution.components:
                        distribution.components.append(cp)

                if mirror_sources:
                    distribution.mirror_sources = mirror_sources
            else:
                raise ValueError(N_("Need a distribution to add properties"))
            session.commit()
            result = True
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Add new properties to a mirrored distribution"))
    def addMirrorProperty(self, distribution=None, arch=None, component=None, mirror_sources=None, origin=None):
        """
        Add properties to an existing distribution mirror definition.

        =============== ============
        Parameter       Description
        =============== ============
        distribution    The distribution name
        arch            List of architectures
        component       List of components
        mirror_sources  Flag to mirror sources
        origin          The URL of the mirrors origin
        =============== ============

        Example:

        >>> proxy.addMirrorProperty(distribution="debian", arch="i386", component="main", mirror_sources=TRUE, origin="http://ftp.debian.org/debian/dists/lenny/")

        ``Return:`` True on success
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(distribution)
                    if not instance:
                        raise ValueError(N_("Distribution %s was not found", distribution))
                    else:
                        distribution = instance
                distribution = session.merge(distribution)
                if arch:
                    if isinstance(arch, StringTypes):
                        instance = self._getArchitecture(arch, add=True)
                        if not instance:
                            raise ValueError(N_("Architecture %s was not found", arch))
                        else:
                            arch = instance
                    session.commit()
                    arch = session.merge(arch)
                    if arch not in distribution.architectures:
                        distribution.architectures.append(arch)
                if component:
                    if isinstance(component, StringTypes):
                        instance = self._getComponent(component, add=True)
                        if not instance:
                            raise ValueError(N_("Component %s was not found", component))
                        else:
                            component = instance
                    session.commit()
                    component = session.merge(component)
                    if component not in distribution.components:
                        distribution.components.append(component)
                if mirror_sources:
                    distribution.mirror_sources = mirror_sources
                if origin:
                    distribution.origin = origin
            else:
                raise ValueError(N_("Need a distribution to add properties"))
            session.commit()
            result = True
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Remove existing properties from a mirrored distribution"))
    def removeMirrorProperty(self, distribution=None, arch=None, component=None):
        """
        Remove properties of an existing distribution mirror definition.

        =============== ============
        Parameter       Description
        =============== ============
        distribution    The distribution name
        arch            List of architectures
        component       List of components
        =============== ============

        ``Return:`` True on success
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(distribution)
                    if not instance:
                        raise ValueError(N_("Distribution %s was not found", distribution))
                    else:
                        distribution = instance
                distribution = session.merge(distribution)
                if arch:
                    if isinstance(arch, StringTypes):
                        instance = self._getArchitecture(arch)
                        if not instance:
                            raise ValueError(N_("Architecture %s was not found", arch))
                        else:
                            arch = instance
                    arch = session.merge(arch)
                    if arch in distribution.architectures:
                        distribution.architectures.remove(arch)
                if component:
                    if isinstance(component, StringTypes):
                        instance = self._getComponent(component)
                        if not instance:
                            raise ValueError(N_("Component %s was not found", component))
                        else:
                            component = instance
                    component = session.merge(component)
                    if component in distribution.components:
                        distribution.components.remove(component)
                else:
                    raise ValueError(N_("Distribution %s has no releases", distribution.name))
            else:
                raise ValueError(N_("Need a distribution to remove properties"))
            session.commit()
            result = True
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Update a local mirror"))
    def updateMirror(self, distribution=None, components=None, architectures=None, sections=None):
        """
        Initially download or update a distribution from a mirror.

        =============== ============
        Parameter       Description
        =============== ============
        distribution    The distribution name
        components      List of components to download
        architectures   List of architectures to download
        sections        List of sections to download
        =============== ============

        Example:

        >>> proxy.updateMirror(distribution="debian", components=["main"], sections=["shells"])

        ``Return:`` True on success
        """
        result = None
        session = None

        try:
            session = self.getSession()
            if distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(distribution)
                    if not instance:
                        raise ValueError(N_("Distribution %s was not found", distribution))
                    else:
                        distribution = instance
                distribution = session.merge(distribution)
                if distribution.releases:
                    result = self.type_reg[distribution.type.name].updateMirror(
                        session,
                        distribution=distribution,
                        releases=releases,
                        components=components,
                        architectures=architectures,
                        sections=sections)
                    distribution.last_updated=datetime.datetime.utcnow()
                else:
                    raise ValueError(N_("Distribution %s has no releases", distribution.name))
            else:
                raise ValueError(N_("Need either a distribution or a list of releases to update"))
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
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

    @Command(__help__=N_("List packages by various criteria"))
    def getPackages(self, release=None, arch=None, component=None, section=None, custom_filter=None,
        offset=None, limit=None):
        """
        List available packages using the specified criteria.

        =============== =================================================================
        Parameter       Description
        =============== =================================================================
        release         Optional release instance or release name
        arch            Optional name or instance of architecture (i.e. 'i386', 'amd64')
        component       Optional name or instance of component (i.e. 'main', 'contrib')
        section         Optional name or instance of section (i.e. 'text', 'utils')
        custom_filter   TODO
        offset          Offset to begin with, starting with 0
        limit           Limit result entries
        =============== =================================================================

        Example:

        >>> proxy.getPackages({'releases':"sqeeze/1.0", 'section':'kernel'})
        ...

        The result list consists of hashes with these keys:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        name                Package name
        files               List of files that belong to this package
        arch                Package architecture
        long_description    Description
        description         Package description
        origin              Source URL
        recommends          List of recommended packages
        suggests            List of dependency suggestsions
        depends             List of dependencies
        build_depends       List of build dependencies
        format              Format of source package
        provides            List of alias names
        maintainer          Contact of the package maintainers
        type                Package type (i.e. deb)
        section             Section this package is part of
        component           Component this package is part of
        standards_version   Standards version for this package
        priority            Package priority
        source              Source URL
        installed_size      Number of bytes that will be used on the harddisk
        =================== ====================================================

        ``Return:`` list of package names
        """
        #TODO: make lists of recommends, etc.
        def package_filter(package):
            if arch and not package.arch.name == arch:
                return False
            if section and not package.section.name == section:
                return False
            if custom_filter:
                if custom_filter.has_key('name'):
                    if package.name.startswith(custom_filter['name']):
                        return True
                    else:
                        return False
            return True

        result = None
        session = None

        try:
            session = self.getSession()
            if arch and isinstance(arch, Architecture):
                arch = session.merge(arch)
                arch = arch.name
            if section and isinstance(section, Section):
                section = session.merge(section)
                section = section.name
            if release and isinstance(release, StringTypes):
                release = self._getRelease(release)
                if release is None:
                    return result
                else:
                    release = session.merge(release)
                    result = filter(package_filter, release.packages)
            else:
                if custom_filter:
                    result = session.query(Package.name.like(custom_filter))
                elif arch or component or section:
                    result = session.query(Package)
                    if arch:
                        result = result.join(Architecture).filter_by(name=arch)
                    if component:
                        result = result.join(Component).filter_by(name=component)
                    if section:
                        result = result.join(Section).filter_by(name=section)
                else:
                    result = session.query(Package).all()
            if limit or offset:
                result = result[offset:][:limit]
            result = [package.getInfo() for package in result]
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Get complete package information based on various criteria"))
    def getPackagesInformation(self, release=None, arch=None, section=None, custom_filter=None,
        offset=None, limit=None):
        """
        Like getPackages, but returns a complete dictionary with package information.
        """
        pass

    @Command(__help__=N_("Get single package information"))
    def getPackageInformation(self, release, arch, package):
        """
        getPackageInformation returns a dictionary containing package information.
        """
        pass

    @Command(__help__=N_("Add a package to the selected distribution/release"))
    def addPackage(self, url, release=None, distribution=None, component=None, updateInventory=True):
        """
        Add one package to a distribution.

        =============== ==================================================================================
        Parameter       Description
        =============== ==================================================================================
        url             Local or remote path to package file (supported remote protocols: http/https/ftp)
        release         (optional) add package to specified release
        distribution    (optional) add package to specified distribution
        component       (optional) override component for package
        updateInventory rebuild packages list after adding package
        =============== ==================================================================================

        Example:

        >>> proxy.addPackage(
        ...   "http://ftp.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1.dsc",
        ...   {"release": "squeeze/1.0"})

        ``Return:`` True on success
        """
        result = None
        download_dir = None
        local_url = None
        session = None
        type_name = None

        try:
            session = self.getSession()
            if release:
                if isinstance(release, StringTypes):
                    instance = self._getRelease(release)
                    if instance is not None:
                        release = instance
                    else:
                        raise ValueError(N_("Release {release} does not exist!").format(release=release))
                session.add(release)

            elif distribution:
                if isinstance(distribution, StringTypes):
                    instance = self._getDistribution(release)
                    if instance is not None:
                        distribution = instance
                    else:
                        raise ValueError(N_("Distribution {distribution} does not exist!").format(distribution=distribution))
                session.add(distribution)
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

            if local_url is None:
                return None

            if os.path.exists(local_url):
                # get file extension
                file_ext = local_url.split('.')[-1]
                if release:
                    type_name = release.distribution.type.name
                elif distribution:
                    type_name = distribution.type.name
                elif file_ext in self.type_reg:
                    type_name = file_ext
                else:
                    raise ValueError(N_("Don't know how to handle {url}").format(url=url))

                # Distribution specific method must handle duplicates
                result = self.type_reg[file_ext].addPackage(session,
                                                            local_url,
                                                            distribution=distribution,
                                                            release=release,
                                                            component=component,
                                                            origin=url)
                if result is not None:
                    session.add(result)
                    result.origin = url
                    session.commit()
                    if updateInventory:
                        self._updateInventory(release=release, distribution=distribution)
            else:
                raise ValueError(N_("Path '{url}' is not readable").format(url=url))

            if download_dir:
                try:
                    shutil.rmtree(download_dir)
                except:
                    pass

        except ValueError:
            raise
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result != None

    @Command(__help__=N_("Remove a package from the selected release"))
    def removePackage(self, package, arch=None, release=None, distribution=None):
        """
        Removes a package from a release.

        =============== ========================
        Parameter       Description
        =============== ========================
        package         Package name
        release         Name of the release
        distribution    Name of the distribution
        arch            Architecture
        =============== ========================

        Example:

        >>> proxy.removePackage("jaaa", release="squeeze/1.0", arch="source")

        ``Return:`` True on success
        """
        result = None
        session = None
        package_name = package

        try:
            session = self.getSession()
            if isinstance(package, StringTypes):
                package = self._getPackage(package, arch=arch)

            if package is not None:
                if isinstance(package, ListType):
                    for package_instance in package:
                        package_instance = session.merge(package_instance)
                        package_name = package_instance.name
                        result = self.type_reg[package_instance.type.name].removePackage(session, package_instance, arch=arch, release=release, distribution=distribution)
                else:
                    package = session.merge(package)
                    package_name = package.name
                    result = self.type_reg[package.type.name].removePackage(session, package, arch=arch, release=release, distribution=distribution)
                session.commit()
            else:
                raise ValueError(N_("Package {package} not found!").format(package=package_name))
        except ValueError:
            raise
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result != None

    def addKeys(self, keys):
        """
        Add keys for repository validation.

        =============== ========================
        Parameter       Description
        =============== ========================
        key             GPG private key block
        =============== ========================

        Example:

        >>> keyring = \"\"\"-----BEGIN PGP PRIVATE KEY BLOCK-----
        ... Version: GnuPG v1.4.10 (GNU/Linux)
        ...
        ... lQHYBEx2RJ8BBADGAvwUiutOLO+OgkpWmOfNczRcEWZSja8jfZJFAHkSknq7t9lM
        ... FD0qYkjxnmGvi44cPmKu7Z2xkBxljyKK5pDOkCqB2QBUrXSnb3rg6/w9gX8Mh1er
        ... e8VZ/45sjxqwoUIPWWsrmEotQ9388KbEhdw14FQj/rai/Xa7rqYI6nVQSQARAQAB
        ... AAP6AyHggTljDsfnvu3ZQj/ihdj27A056XmOJ4elkobqNpfsdI9l8t3fy4dFvy28
        ... 8gKvnzG08uG1iyD1mnBho/sdytTKe7GMLDcHyWWBOl31WLKUzQFTOpQ6EjzKNyNl
        ... CGvwSKBm8u81BfNi7FpfgnVI733jdqZ8Lvq5znKRrK4WJdECANOaZn78oghTONUQ
        ... 1Fo6PgrjFkD337TR3Dm5tllp0Mlly9C9/N5CiTZj/0VLNyzT0tHVik8WEmF37bgY
        ... Zd2gA9kCAO+Oj6k9Bqs6uTjHFmT5NEGvoJVSd4Q+F4jDmT+U2yJEBUk1dHiRAcEr
        ... NcRU5VMbpBk9rbsmikX0oA1gavaNmfECAJi9uX99nb+dNWpqFqHxuDKaHapG9cKv
        ... AlI+btxIAzPFvqMuHMjFKn6T57D8QpIz1f7LdmlYKKOr3DRmaYOaJBClOrQ2QXV0
        ... b2dlbmVyYXRlZCBLZXkgKEdlbmVyYXRlZCBieSBnbnVwZy5weSkgPGphbndAaG9t
        ... ZXI+iLgEEwECACIFAkx2RJ8CGy8GCwkIBwMCBhUIAgkKCwQWAgMBAh4BAheAAAoJ
        ... ELxLvnLaEqJwX2oD/2wAOYbZG68k7iDOqFI1TpQjlgRQKHNuvindjWrPjfgsDfZH
        ... kEhidYX1IRzgyhhLjrPDcB0RTcnjlXm9xOXJb3tcuyKWxi2CHMstdgTMHt6xb37o
        ... LcWMU6gayNYj7eMgCOFM6ywySRS81FC+PPnr147xbp5FwgmoPRK52MURsHJ+
        ... =RwlJ
        ... -----END PGP PRIVATE KEY BLOCK-----\"\"\"
        >>> manager = LibinstManager()
        >>> manager.addKeys(keyring)

        ``Return:`` True on success
        """
        result = False
        session = None
        repository = None

        try:
            session = self.getSession()
            repository = self._getRepository(path=self.path)
            session.add(repository)

            if not repository.keyring:
                self._addRepositoryKeyring(repository=repository, keyring=RepositoryKeyring(data=keys))
                session.refresh(repository)
                work_dir = self._getGPGEnvironment()
                gpg = gnupg.GPG(gnupghome=work_dir)
                for key in gpg.list_keys(True):
                    if key['type'] == "sec":
                        repository.keyring.name = key['fingerprint']
                        break
                shutil.rmtree(work_dir)
                result = True
            else:
                work_dir = self._getGPGEnvironment()
                gpg = gnupg.GPG(gnupghome=work_dir)
                # pylint: disable-msg=E1101
                import_result = gpg.import_keys(keys)
                if import_result.count > 0:
                    result = True
                shutil.rmtree(work_dir)

            session.commit()

        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def removeKey(self, key_id):
        """
        Remove key with given fingerprint.

        =============== ========================
        Parameter       Description
        =============== ========================
        key_id          Key fingerprint
        =============== ========================

        Example:

        >>> manager = LibinstManager()
        >>> manager.removeKey("BC4BBE72DA12A270")

        ``Return:`` True on success
        """
        result = None
        session = None
        work_dir = self._getGPGEnvironment()
        gpg = gnupg.GPG(gnupghome=work_dir)
        fp = None
        for key in gpg.list_keys(True):
            if key['keyid'] == key_id or key['fingerprint'] == key_id:
                fp = key['fingerprint']
                break
        if fp is not None:
            if gpg.delete_keys(fp, secret=True).status == "ok":
                try:
                    session = self.getSession()
                    repository = self._getRepository(path=self.path)
                    repository = session.merge(repository)
                    repository.keyring.data = gpg.list_keys(True)
                    if repository.keyring.name == fp:
                        repository.keyring.name = None
                    session.commit()
                    result = True
                except:
                    session.rollback()
                finally:
                    session.close()
        shutil.rmtree(work_dir)
        return result

    def listKeys(self):
        """
        List available keys.

        Example:

        >>> manager = LibinstManager()
        >>> manager.listKeys()
        []

        ``Return:`` list of key_id/key pairs
        """
        result = None
        try:
            session = self.getSession()
            repository = self._getRepository(path=self.path)
            session.add(repository)
            if repository.keyring is not None:
                work_dir = self._getGPGEnvironment()
                gpg = gnupg.GPG(gnupghome=work_dir)
                result = gpg.list_keys(True)
                shutil.rmtree(work_dir)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Returns a list of items of item_type (if given) for the specified release - or all."))
    def listConfigItems(self, release, item_type=None, path=None, children=None):
        """
        List configuration items for given release.

        =============== =================================================================
        Parameter       Description
        =============== =================================================================
        release         Name of the release to list config items of
        item_type       Filter items by type
        path            Filter items by path
        children        Filter items by children
        =============== =================================================================

        Example:

        >>> proxy.listConfigItems('squeeze/1.0')
        {'/gon-base/sudoers': 'PuppetFile', '/gon-base': 'PuppetModule', '/gon-base/users': 'PuppetManifest', '/gon-base/sudo': 'PuppetManifest', '/': 'PuppetRoot'}

        ``Return:`` dict path/type pair
        """
        result = None
        session = None
        try:
            session = self.getSession()
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
            release = session.merge(release)
            if release.distribution.installation_method is None:
                raise ValueError("Release %s has no installation method!" % release.name)
            elif release.distribution.installation_method not in self.install_method_reg:
                raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method, release.name))
            else:
                result = self.install_method_reg[release.distribution.installation_method].listItems(release.name, item_type=item_type, path=path, children=children)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Returns a list of all asignable elements for a release"))
    def listAssignableElements(self, release):
        """
        List items that can be assigned to a client for a specific release.

        =============== =================================================================
        Parameter       Description
        =============== =================================================================
        release         Name of the release to list config items of
        =============== =================================================================

        Example:

        >>> proxy.listAssignableElements('squeeze/1.0')
        {'gon-base::users': {'parameter': {'starting_uid': 'this global variable is used to set the minimum uid used for our users\n\n'}, 'description': 'This class installs our default set of users in our servers'}, 'gon-base::sudo': {'parameter': {}, 'description': 'This class installs our default sudoers file.'}}

        The resulting dictionary contains the assignable object name as the key and
        potential parameter descriptions as a nested dict:

        =================== ====================================================
        Key                 Description
        =================== ====================================================
        parameter           Parameter dictionary
        description         Item description
        =================== ====================================================

        ``Return:`` dict
        """
        result = None
        session = None
        try:
            session = self.getSession()
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
            release = session.merge(release)
            if release.distribution.installation_method is None:
                raise ValueError("Release %s has no installation method!" % release.name)
            elif release.distribution.installation_method not in self.install_method_reg:
                raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method, release.name))
            else:
                result = self.install_method_reg[release.distribution.installation_method].listAssignableElements(release.name)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Set the data for the specified item"))
    def setConfigItem(self, release, path, item_type, data):
        """
        Create or update item by setting specified parameters.

        ========== ===========================================
        Parameter  Description
        ========== ===========================================
        release    Release name
        path       Path to the item
        item_type  Type of the target item
        data       Parameter dict containing item information
        ========== ===========================================

        Example:

        >>> proxy.setConfigItem('wheezy', '/module', 'PuppetModule',
        ... {'dependency': [],
        ...  'version': '42',
        ...  'description': 'A senseles puppet module'})

        ``Return:`` True on success
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)
            if release.distribution.installation_method is None:
                raise ValueError("Release %s has no installation method!" % release.name)
            elif release.distribution.installation_method not in self.install_method_reg:
                raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method, release.name))
            else:
                result = self.install_method_reg[release.distribution.installation_method].setItem(release.name, path, item_type, data)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result != None

    @Command(__help__=N_("Remove the specified item and it's children"))
    def removeConfigItem(self, release, path, children=None):
        """
        Remove specified item.

        ========== ===========================================
        Parameter  Description
        ========== ===========================================
        release    Release name
        path       Path to the item
        children   Remove children
        ========== ===========================================

        Example:

        >>> proxy.removeConfigItem('squeeze', '/module')

        ``Return:`` True on success
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)
            if release.distribution.installation_method is None:
                raise ValueError("Release %s has no installation method!" % release.name)
            elif release.distribution.installation_method not in self.install_method_reg:
                raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method,
                            release.name))
            else:
                result = self.install_method_reg[release.distribution.installation_method].removeItem(release.name, path, children)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result != None

    @Command(__help__=N_("Return the data of specified item"))
    def getConfigItem(self, release, path):
        """
        Get a dict describing the addressed config item.

        ========== ===========================================
        Parameter  Description
        ========== ===========================================
        release    Release name
        path       Path to the item
        ========== ===========================================

        Example:

        >>> proxy.getConfigItem('squeeze/1.0', '/gon-base')
        {'dependency': [], 'version': '11', 'name': 'gon-base', 'description': None}

        The resulting dict depends on the parameters that are possible
        for the defined item.

        ``Return:`` dict
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)
            if release.distribution.installation_method is None:
                raise ValueError("Release %s has no installation method!" % release.name)
            elif release.distribution.installation_method not in self.install_method_reg:
                raise ValueError("Unsupported installation method %s found for release %s " % (release.distribution.installation_method,
                            release.name))
            else:
                result = self.install_method_reg[release.distribution.installation_method].getItem(release.name, path)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    @Command(__help__=N_("Get supported system locales"))
    def getSystemLocales(self):
        """
        List available system locales.

        Example:

        >>> proxy.getSystemLocales()
        {'sk_SK.UTF-8': 'Slovak', 'ml_IN.UTF-8': 'Malayalam (India)', 'ar_QA.UTF-8': 'Arabic (Qatar)', ...}

        ``Return:`` dict
        """
        return locale_map

    @Command(__help__=N_("Get supported keyboard models"))
    def getKeyboardModels(self):
        """
        List available keyboard models.

        Example:

        >>> proxy.getKeyboardModels()
        {'gr': ['Greek', 'gr,us', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'], ... }

        ``Return:`` dict
        """
        return self.keyboardModels

    @Command(__help__=N_("Get supported time zones"))
    def getTimezones(self):
        """
        List available timezones.

        Example:

        >>> proxy.getTimezones()
        ['Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa', ...]

        ``Return:`` list
        """
        return pytz.all_timezones

    @Command(__help__=N_("Get kernel packages for the specified release"))
    def getKernelPackages(self, release):
        """
        Get a dict describing the available kernel packages for a release.

        ========== ===========================================
        Parameter  Description
        ========== ===========================================
        release    Release name
        ========== ===========================================

        Example:

        >>> proxy.getKernelPackages('squeeze/1.0')
        [{'files': [{'md5sum': '4b827524cf3d3c77e91f4afa089cf196', 'name': 'linux-image-2.6.32-5-xen-amd64_2.6.32-31_amd64.deb', 'size': '28592546'}], 'origin': 'http://ftp.de.debian.org/debian/pool/main/l/linux-2.6/linux-image-2.6.32-5-xen-amd64_2.6.32-31_amd64.deb', 'recommends': 'firmware-linux-free (>= 2.6.32)', 'maintainer': 'Debian Kernel Team <debian-kernel@lists.debian.org>', 'description': 'Linux 2.6.32 for 64-bit PCs, Xen dom0 support', 'format': None, 'type': 'deb', 'section': 'kernel', 'suggests': 'linux-doc-2.6.32, grub', 'component': 'main', 'standards_version': '2.0', 'priority': 'optional', 'source': 'linux-2.6', 'depends': 'module-init-tools, linux-base (>= 2.6.32-31), initramfs-tools (>= 0.55)', 'version': '2.6.32-31', 'build_depends': None, 'provides': 'linux-image, linux-image-2.6, linux-modules-2.6.32-5-xen-amd64', 'installed_size': '97340', 'arch': 'amd64', 'long_description': '  The Linux kernel 2.6.32 and modules for use on PCs with AMD64 or Intel 64\n  processors.\n  .\n  This kernel also runs on a Xen hypervisor.  It supports both privileged\n  (dom0) and unprivileged (domU) operation.', 'name': 'linux-image-2.6.32-5-xen-amd64'}]

        The result is a package list like delivered by
        :meth:`libinst.manage.LibinstManager.getPackages`.

        ``Return:`` dict
        """
        result = None
        session = None
        try:
            session = self.getSession()
            if isinstance(release, StringTypes):
                instance = self._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)
            distribution = release.distribution
            repo_type = distribution.type.name
            pname = self.type_reg[repo_type].getKernelPackageFilter()
            result = self.getPackages(release=release.name, custom_filter={'name': pname})
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    @Command(__help__=N_("Completely remove device's installation parameters"))
    def removeBaseInstallParameters(self, device_uuid):
        """
        Disable device base install capabilities.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique identifier of a device
        =========== ===========================================

        ``Return:`` True on success
        """
        data = load_system(device_uuid)
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        inst_m = self.base_install_method_reg[method]
        return inst_m.removeBaseInstallParameters(device_uuid, data)

    @Command(__help__=N_("Get device's installation method"))
    def systemGetBaseInstallMethod(self, device_uuid, data=None):
        """
        Return the systems base install method.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique identifier of a device
        data        *Reserved for internal use*
        =========== ===========================================

        Example:

        >>> proxy.systemGetBaseInstallMethod('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        'preseed'

        ``Return:`` String describing the base install method
        """
        # Load system
        if not data:
            data = load_system(device_uuid)

        if not "installTemplateDN" in data:
            return None

        # Load template and get the install method
        lh = LDAPHandler.get_instance()

        with lh.get_handle() as conn:
            res = conn.search_s(data['installTemplateDN'][0], ldap.SCOPE_BASE,
                "(cn=*)", ['installMethod'])

        return res[0][1]["installMethod"][0].lower()

    @Command(__help__=N_("Get device's configuration method"))
    def systemGetConfigMethod(self, device_uuid, data=None):
        """
        Return the systems configuration method.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique identifier of a device
        data        *Reserved for internal use*
        =========== ===========================================

        Example:

        >>> proxy.systemGetConfigMethod('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        'puppet'

        ``Return:`` Template as a string
        """
        if not data:
            data = load_system(device_uuid)

        if not "configMethod" in data:
            return None

        return data["configMethod"][0].lower()

    @Command(__help__=N_("Get device's boot string"))
    def systemGetBootString(self, device_uuid, mac=None):
        """
        Return the systems PXE boot string based on either the
        device UUID or the MAC address.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Optional unique identifier of a device
        mac         Optional MAC
        =========== ===========================================

        Example:

        >>> proxy.systemGetBootString('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        u'label preseed\n    kernel debian-installer/i386/linux\n    append vga=normal initrd=debian-installer/i386/initrd.gz netcfg/choose_interface=eth0 locale=de_DE debian-installer/country=DE debian-installer/language=de debian-installer/keymap=de-latin1-nodeadkeys console-keymaps-at/keymap=de-latin1-nodeadkeys auto-install/enable=false preseed/url=https://amqp.intranet.gonicus.de:8080/preseed/de-ad-d9-57-56-d5 debian/priority=critical hostname=dyn-10 domain=please-fixme.org DEBCONF_DEBUG=5 svc_key=f1p8zRBGrUA26Nn+2qBS/JC8KOXHTEfgIEq5Le2WC4jW2xUuVzzHnO9LYiH8hYLNXHo7V9+2Aiz8\n/XU6xxcusWUiMjXgdZcDe8wJtXR5krg=\n\n'

        ``Return:`` Template as a string
        """
        params = []
        data = load_system(device_uuid, mac)
        device_uuid = data['deviceUUID'][0]
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        c_method = self.systemGetConfigMethod(device_uuid)

        # Use the method described by "method" and pass evaluated data
        if not method in self.base_install_method_reg:
            raise ValueError("device with UUID '%s' has an unknown installation method assigned" % device_uuid)

        # Load base install parameters
        inst_m = self.base_install_method_reg[method]
        params += inst_m.getBootParams(device_uuid)

        # Load config parameters
        if c_method:
            conf_m = self.install_method_reg[c_method]
            params += conf_m.getBootParams(device_uuid)

        # Check device status before returning anything
        if not "deviceStatus" in data or "A" not in data["deviceStatus"][0]:
            return None

        # Append device key if available
        if "deviceKey" in data:
            params.append("svc_key=%s" % encode(data["deviceKey"][0]))

        #TODO: for non DNS/zeroconf setups, it might be a good idea to
        #      send a connection URI, too

        return inst_m.getBootString(device_uuid) % " ".join(params)

    @Command(__help__=N_("Get device's boot configuration"))
    def systemGetBootConfiguration(self, device_uuid, mac=None):
        """
        Return the systems base install template based on either the
        device UUID or the MAC address.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Optional unique identifier of a device
        mac         Optional MAC
        =========== ===========================================

        Example:

        >>> proxy.systemGetTemplate('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        'the template code'

        ``Return:`` Template as a string
        """
        data = load_system(device_uuid, mac)
        device_uuid = data['deviceUUID'][0]
        method = self.systemGetBaseInstallMethod(device_uuid, data)

        # Use the method described by "method" and pass evaluated data
        if not method in self.base_install_method_reg:
            raise ValueError("device with UUID '%s' has an unknown installation method assigned" % device_uuid)

        # Get boot configuration from installation method
        inst_m = self.base_install_method_reg[method]
        return inst_m.getBootConfiguration(device_uuid)

    @Command(__help__=N_("Get device's base install parameters"))
    def systemGetBaseInstallParameters(self, device_uuid):
        """
        Return the systems base install parameters that are used
        to fill up the template.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Optional unique identifier of a device
        =========== ===========================================

        Example:

        >>> proxy.systemGetBaseInstallParameters('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        {'utc': ['TRUE'], 'ntp-servers': ['1.2.3.4'], 'kernel': ['linux-image-2.6.32-5-xen-amd64'], 'root-hash': ['{CRYPT}'], 'root-user': ['TRUE'], 'disk-setup': ['disk sda --initlabel --none;part pv.00 --size 1000 --ondisk sda;volgroup Kaese --format pv.00;'], 'template': '<snip>', 'system-locale': ['de_DE.UTF-8'], 'release': ['debian/squeeze/1.0'], 'timezone': ['Europe/Berlin'], 'keyboard-layout': ['de-latin1-nodeadkeys']}

        Please take a look at
        :meth:`libinst.manage.LibinstManager.systemSetBaseInstallParameters`
        for more information about the returned properties.

        ``Return:`` dict of properties
        """
        data = load_system(device_uuid, None, False)
        method = self.systemGetBaseInstallMethod(device_uuid, data)
        inst_m = self.base_install_method_reg[method]
        return inst_m.getBaseInstallParameters(device_uuid, data)

    @Command(__help__=N_("Set device's base install parameters"))
    def systemSetBaseInstallParameters(self, device_uuid, data):
        """
        Set the system base install parameters that are used
        to fill up the template.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique device identifier
        data        Dictionary specifying the properties
        =========== ===========================================

        The data dictionary has the following property keys (**values are
        always lists**):

        =============== ======================================================
        Key             Description
        =============== ======================================================
        utc             Flag to specify if system uses UTC
        timezone        String to specify time zone
        ntp-servers     List of time server names/IPs
        kernel          The boot kernel package name
        root-hash       Hashed version of the root password
        root-user       Flag to decide if there's a root user
        disk-setup      String oriented at the RedHat kickstart device string
        template        String containing the system template
        system-locale   Locale definition for the system
        release         Release to install on the system
        keyboard-layout Keyboard layout to use
        =============== ======================================================

        These are the absolute base settings needed to install a device,
        additional stuff is done by configuration methods.

        ``Return:`` True on success
        """
        sys_data = load_system(device_uuid, None, False)
        method = self.systemGetBaseInstallMethod(device_uuid, data)

        # If there's no method, we're new. Look for the method in the
        # template.
        if not method:
            tmp = self.installGetTemplate(data['template'])
            method = tmp['method']

        inst_m = self.base_install_method_reg[method]
        return inst_m.setBaseInstallParameters(device_uuid, data, sys_data)

    @Command(__help__=N_("Get device's config parameters"))
    def systemGetConfigParameters(self, device_uuid):
        """
        Return the systems config parameters that are used
        to provision the config management system.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Optional unique identifier of a device
        =========== ===========================================

        Example:

        >>> proxy.systemGetConfigParameters('2daf7cbf-75c2-4ea3-bfec-606fe9f07051')
        {'var': {'starting_uid': ''}, 'item': ['gon-base::sudo', 'gon-base::users'], 'method': 'puppet'}

        Please take a look at
        :meth:`libinst.manage.LibinstManager.systemSetConfigParameters`
        for more information about the returned properties.

        ``Return:`` dict of properties
        """


        sys_data = load_system(device_uuid, None, False)
        method = self.systemGetConfigMethod(device_uuid)

        if not method in self.install_method_reg:
            return None

        config_m = self.install_method_reg[method]
        return config_m.getConfigParameters(device_uuid, sys_data)

    @Command(__help__=N_("Set device's config parameters"))
    def systemSetConfigParameters(self, device_uuid, data):
        """
        Set the system config parameters that are used
        provision the config management system.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique device identifier
        data        Dictionary specifying the properties
        =========== ===========================================

        The data dictionary has the following property keys:
        always lists**):

        ====== ===================================
        Key    Description
        ====== ===================================
        item    List of assigned items
        method  Config management method to use
        var     Dict of variables and their values
        ====== ===================================

        ``Return:`` True no success
        """
        sys_data = load_system(device_uuid, None, False)
        method = data['method']

        if not method in self.install_method_reg:
            return None

        config_m = self.install_method_reg[method]
        config_m.setConfigParameters(device_uuid, data, sys_data)

    @Command(__help__=N_("Completely remove device's config parameters"))
    def removeConfigParameters(self, device_uuid):
        """
        Disable device configuration managmenet.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique identifier of a device
        =========== ===========================================

        ``Return:`` True on success
        """
        sys_data = load_system(device_uuid, None, False)
        method = self.systemGetConfigMethod(device_uuid)

        if not method in self.install_method_reg:
            return None

        config_m = self.install_method_reg[method]
        return config_m.removeConfigParameters(device_uuid, sys_data)

    @Command(__help__=N_("Get list of templates, filter by method"))
    def installListTemplates(self, method=None):
        """
        List available templates - optionally by method.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        method      Optional method to filter for
        =========== ===========================================

        Example:

        >>> agent.installListTemplates()
        {'test': {'description': 'test', 'method': 'preseed'}, 'debian-test': {'description': 'Test', 'method': 'preseed'}}

        The resulting dict has the template name as key and a property
        dict with these keys:

        =========== ====================================
        Key         Description
        =========== ====================================
        method      Name of the assigned template method
        description Description of the template
        =========== ====================================

        ``Return:`` dict describing templates
        """
        result = {}
        lh = LDAPHandler.get_instance()
        fltr = "installMethod=%s" % method if method else "cn=*"

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=installTemplate)(%s))" % fltr,
                ["cn", "description", "installMethod"])

        for entry in res:
            entry = dict(map(lambda x: (self.template_map[x[0]], x[1][0]), entry[1].items()))
            result[entry['name']] = {'description': entry['description'], 'method': entry['method']}

        return result

    @Command(__help__=N_("Get template by name"))
    def installGetTemplate(self, name):
        """
        Get template by name

        =========== ==============
        Parameter   Description
        =========== ==============
        name        Template name
        =========== ==============

        Example:

        >>> agent.installGetTemplate('debian-test')
        ...

        Please take a look at
        :meth:`libinst.manage.LibinstManager.installSetTemplate`
        for more information about the returned properties.

        ``Return:`` dict describing template
        """
        lh = LDAPHandler.get_instance()
        fltr = "cn=%s" % name

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=installTemplate)(%s))" % fltr,
                self.template_map.keys())

        if len(res) != 1:
            raise ValueError("no template named '%s' available" % name)

        entry = dict(map(lambda x: (self.template_map[x[0]], x[1][0]), res[0][1].items()))
        if 'data' in entry:
            entry['data'] = unicode(entry['data'], "utf-8")
        return entry

    @Command(__help__=N_("Set template by name"))
    def installSetTemplate(self, name, data):
        """
        Set template by name and data.

        =========== ==============
        Parameter   Description
        =========== ==============
        name        Template name
        data        Template data
        =========== ==============

        *data* is a dictionary with these keys:

        =========== ====================================
        Key         Description
        =========== ====================================
        method      Name of the assigned template method
        description Description of the template
        data        The template string
        =========== ====================================
        """
        lh = LDAPHandler.get_instance()
        fltr = "cn=%s" % name

        if not name:
            raise ValueError("template needs a name")

        data['name'] = name

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=installTemplate)(%s))" % fltr,
                self.template_map.keys())

            create_new = len(res) == 0

            if len(res) > 1:
                raise ValueError("no template named '%s' available" % name)

            mods = []
            if create_new:
                #TODO: unique check
                mods.append(('objectClass', ['gosaConfigItem', 'installTemplate']))
                dn = ",".join(["cn=" + name,
                    self.env.config.get("libinst.template-rdn", "cn=templates,cn=libinst,cn=config"),
                    lh.get_base()])
                res = {}
            else:
                dn = res[0][0]
                res = res[0][1]

            for ldap_key, key in self.template_map.items():
                if ldap_key in res and not key in data:
                    mods.append((ldap.MOD_DELETE, ldap_key))
                elif ldap_key in res and key in data and unicode(res[ldap_key][0], "utf-8") != data[key]:
                    mods.append((ldap.MOD_REPLACE, ldap_key,
                        [data[key].encode("utf-8")]))
                elif key in data and not ldap_key in res:
                    if create_new:
                        mods.append((ldap_key,
                            [data[key].encode("utf-8")]))
                    else:
                        mods.append((ldap.MOD_REPLACE, ldap_key,
                            [data[key].encode("utf-8")]))

            # Assemble entry and write it to the directory
            if create_new:
                conn.add_s(dn, mods)
            else:
                conn.modify_s(dn, mods)

    @Command(__help__=N_("Remove template by name"))
    def installRemoveTemplate(self, name):
        """
        Remove existing template by name.

        =========== ==============
        Parameter   Description
        =========== ==============
        name        Template name
        =========== ==============
        """
        lh = LDAPHandler.get_instance()
        fltr = "cn=%s" % name

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=installTemplate)(%s))" % fltr,
                self.template_map.keys())

            if len(res) != 1:
                raise ValueError("no template named '%s' available" % name)

            conn.delete(res[0][0])

    @Command(__help__=N_("Perpare system for config methods"))
    def prepareSystem(self, device_uuid):
        """
        Prepare a client device for beeing managed by the
        configured config management method. This may create
        some account or install a daemon - or whatever is needed
        to manage it.

        =========== =======================
        Parameter   Description
        =========== =======================
        device_uuid Unique ID of the device
        =========== =======================
        """

        # Check for config recipe tasks
        method = self.systemGetConfigMethod(device_uuid)
        if method in self.install_method_reg:
            config_m = self.install_method_reg[method]
            try:
                config_m.addClient(device_uuid)
            except:
                pass

    def _getArchitecture(self, name, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Architecture).filter_by(name=name).one()
            except NoResultFound:
                if add:
                    result = Architecture(name)
                    session.add(result)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    def _getSection(self, name, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Section).filter_by(name=name).one()
            except NoResultFound:
                if add:
                    result = Section(name)
                    session.add(result)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    def _getComponent(self, name, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Component).filter_by(name=name).one()
            except NoResultFound:
                if add:
                    result = Component(name)
                    session.add(result)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    def _getFile(self, url, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = self._session.query(File).filter_by(name=os.path.basename(url)).one()
            except NoResultFound:
                if add:
                    result = File(name=os.path.basename(url))
                    session.add(result)
                    if os.path.exists(url):
                        infile = open(url, 'rb')
                        content = infile.read()
                        infile.close()
                        m = hashlib.md5()
                        m.update(content)
                        result.md5sum = m.hexdigest()
                        result.size = os.path.getsize(url)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _getType(self, name, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Type).filter_by(name=name).one()
            except NoResultFound:
                if add:
                    result = Type(name)
                    session.add(result)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _getDistribution(self, name):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Distribution).filter_by(name=name).one()
            except NoResultFound:
                pass
        except:
            session.rollback()
            raise

        finally:
            session.close()

        return result

    def _getRelease(self, name):
        result = None
        session = None

        try:
            session = self.getSession()
            result = session.query(Release).filter_by(name=name).one()
            session.commit()
        except NoResultFound:
            pass
        finally:
            session.close()
        return result

    def _getRepository(self, name=None, path=None, add=False):
        result = None
        session = None

        try:
            try:
                session = self.getSession()
                result = session.query(Repository)
                if name:
                    result = result.filter_by(name=name)
                elif path:
                    result = result.filter_by(path=path)
                result = result.one()
            except NoResultFound:
                if add:
                    result = Repository(name=name, path=path)
                    session.add(result)
                    session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _getPackage(self, name, arch=None):
        result = None
        session = None

        try:
            session = self.getSession()
            result = session.query(Package).filter_by(name=name)
            if arch:
                if isinstance(arch, StringTypes):
                    arch = self._getArchitecture(arch)
                arch = session.merge(arch)
                result = result.filter_by(arch=arch)
            if result.count() > 1:
                result = result.all()
            elif result.count() == 1:
                result = result.one()
        except:
            session.rollback()
            raise
        finally:
            session.close()

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
        session = None

        try:
            session = self.getSession()
            if release:
                if isinstance(release, StringTypes):
                    release = self._getRelease(release)
                release = session.merge(release)
                result = self.type_reg[release.distribution.type.name]._updateInventory(session, release=release)
            elif distribution:
                if isinstance(distribution, StringTypes):
                    distribution = self._getDistribution(distribution)
                distribution = session.merge(distribution)
                result = self.type_reg[distribution.type.name]._updateInventory(session, distribution=distribution)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _getAssignableElements(self, release=None):
        result = []
        session = None

        try:
            session = self.getSession()
            result = session.query(ConfigItem).filter_by(assignable=True)
            result = result.join(ConfigItemReleases).join(Release).filter_by(name=release)
            session.commit()

        except:
            session.rollback()
            raise

        finally:
            session.close()

        return result

    def _getConfigItem(self, name, item_type, release=None, add=False):
        result = None
        session = None

        try:
            session = self.getSession()
            try:
                result = session.query(ConfigItem)
                if name:
                    result = result.filter_by(name=name)
                if item_type:
                    result = result.filter_by(item_type=item_type)
                if release:
                    if isinstance(release, Release):
                        release = session.merge(release)
                        release = release.name
                    result = result.join(ConfigItemReleases).join(Release).filter_by(name=release)
                result = result.one()
            except NoResultFound:
                if add:
                    result = ConfigItem(name=name, item_type=item_type)
                    if release:
                        if isinstance(release, StringTypes):
                            release = self._getRelease(release)
                        release = session.merge(release)
                        result.release.append(release)
                    session.add(result)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _replaceConfigItems(self, release, items):
        result = None
        session = None

        try:
            session = self.getSession()

            if isinstance(release, StringTypes):
                release = self._getRelease(release)
            release = session.merge(release)

            # Iterate over DB Items, delete orphans
            for item_name, item_type in self.listItems(release).iteritems():
                if self._getConfigItem(item_name, item_type, release=release):
                    if item_name not in items:
                        db_instance = self._getConfigItem(item_name, item_type, release=release)
                        db_instance = session.merge(db_instance)
                        release.config_items.remove(db_instance)
                        session.delete(db_instance)

            # Iterate over FS scan, add missing items
            for item_name, item_type in items.iteritems():
                if not self._getConfigItem(item_name, item_type, release=release):
                    db_instance = self._getConfigItem(item_name, item_type, release=release, add=True)
                    session.add(db_instance)
                    release.config_items.append(db_instance)

            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result

    def listItems(self, release, item_type=None, path=None, children=None):
        res = {}
        session = None

        def filter_items(item):
            path_match = True
            if path:
                path_match = item.name.startswith(path + "/")

            if item_type:
                return path_match and (item_type == item.item_type)

            return path_match

        try:
            session = self.getSession()

            if not children:
                children = self._getRelease(release).config_items

            children = session.merge(children)
            items = filter(filter_items, children)
            res = dict((i.getPath(), i.item_type) for i in items)

            # Iterate for items with children
            for item in filter(lambda i: i.children, items):
                res.update(self.listItems(release, item_type, path, item.children))

            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return res

    #============================================
    # return the session to be used in the tests.
    #============================================
    def getSession(self):
        return self.env.getDatabaseSession("repository")


    def _addRepositoryKeyring(self, repository=None, keyring=None):
        result = None
        session = None

        try:
            session = self.getSession()
            repository = session.merge(repository)
            repository.keyring = keyring
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result


    def _getGPGEnvironment(self):
        result = None
        session = None
        repository = None

        try:
            session = self.getSession()
            repository = self._getRepository(path=self.path)
            session.add(repository)

            work_dir = tempfile.mkdtemp()
            gpg = gnupg.GPG(gnupghome=work_dir)
            if not repository.keyring:
                #TODO: Config options for key type and length?
                key_type = "RSA"
                key_length = 1024
                self.log.debug("Generating GPG Key, type %s and length %s Bit" % (key_type, key_length))
                input_data = gpg.gen_key_input(key_type=key_type, key_length=key_length)
                key = gpg.gen_key(input_data)
                self._addRepositoryKeyring(repository=repository, keyring=RepositoryKeyring(name=key.fingerprint, data=gpg.export_keys(key, True)))
            else:
                gpg.import_keys(repository.keyring.data)
            result = work_dir
            session.commit()

        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result
