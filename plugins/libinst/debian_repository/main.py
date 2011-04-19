# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: main.py 1242 2010-10-22 06:58:29Z janw $$

 See LICENSE for more information about the licensing.
"""
import string
import os
import sys
import shutil
import hashlib
import subprocess
import gnupg
import tempfile
import urllib2
import re
import gettext

from sqlalchemy.orm.exc import NoResultFound

try:
    # pylint: disable-msg=F0401
    from debian import debfile, deb822
except:
    # pylint: disable-msg=E0611
    from debian_bundle import debfile, deb822


from gosa.common.env import Environment
from gosa.common.utils import N_

from libinst.interface import DistributionHandler

from debian_repository.entities.package import DebianPackage
from debian_repository.entities.priority import DebianPriority
from debian_repository.entities.distribution import DebianDistribution
from debian_repository.entities.release import DebianRelease

# pylint: disable-msg=E0611
from pkg_resources import resource_filename

# Include locales
t = gettext.translation('messages', resource_filename("debian_repository", "locale"), fallback=True)
_ = t.ugettext

class DebianHandler(DistributionHandler):

    def __init__(self):
        self.env = Environment.getInstance()

    @staticmethod
    def getRepositoryTypes():
        return ['deb', 'udeb', 'dsc']

    def createDistribution(self, session, name, mirror=None):
        result = DebianDistribution(name)
        if mirror:
            result.managed = False
            result.origin = mirror
        else:
            result.managed = True
        return result

    def removeDistribution(self, session, distribution, recursive=False):
        result = None
        dists_path = os.sep.join((distribution.repository.path, distribution.name))
        try:
            if os.path.exists(dists_path):
                shutil.rmtree(dists_path)
            result = True
        except:
            raise
        return result

    def createRelease(self, session, distribution, name):
        result = None
        parent = None
        if distribution:
            if '/' in name:
                instance = self._getRelease(session, name.rsplit('/', 1)[0])
                if instance is None:
                    raise ValueError(N_("Parent release {parent} was not found").format(parent=parent))
                else:
                    parent=instance
            result = DebianRelease(name=name, parent=parent)
        return result

    def removeRelease(self, session, release, recursive=False):
        result = None
        dists_path = os.sep.join((release.distribution.repository.path, release.distribution.name, "dists",  release.name.replace('/', os.sep)))
        try:
            if os.path.exists(dists_path):
                shutil.rmtree(dists_path)
            result = True
        except:
            raise
        return result

    def addPackage(self, session, url, distribution=None, release=None, origin=None, component=None):
        if distribution:
            if isinstance(distribution, (str, unicode)):
                distribution = self._getDistribution(session, distribution)
        if release:
            if isinstance(release, (str, unicode)):
                release = self._getRelease(session, release)

        result = self._getPackageFromUrl(session, url, origin=origin,
                                         component=component)
        if release:
            # TODO: Find a better way to code this
            present = False
            upgrade = False
            for p in release.packages:
                if p.name == result.name and p.arch.name == result.arch.name and p.version == result.version:
                    self.env.log.warning("Package %s | version %s | arch %s already present!" % (result.name, result.version, result.arch.name))
                    present = True
                elif p.name == result.name and p.arch.name == result.arch.name and p.version != result.version:
                    upgrade = True
                elif p.name == result.name and p.arch.name != result.arch.name and p.version == result.version:
                    pass

            if present:
                result = None
            else:
                if upgrade: # upgrade means also downgrade
                    if not self.removePackage(session, result.name, arch = result.arch, release = release):
                        result = None

                if result is not None:
                    # Copy file to pool
                    pool_path = os.sep.join((release.distribution.repository.path, "pool", release.distribution.type.name, result.component.name))
                    if result.name.startswith('lib'):
                        pool_path += os.sep + str(result.name).lower()[:3]
                    else:
                        pool_path += os.sep + str(result.name).lower()[0]
                    pool_path += os.sep + result.name.lower()
                    if not os.path.exists(pool_path):
                        os.makedirs(pool_path)

                    for file in result.files:
                        if not os.path.exists(pool_path + os.sep + file.name):
                            shutil.copy2(url, pool_path + os.sep + file.name)

                    ## Manage DB content, update associative properties
                    release.packages.append(result)
                    if not result.arch in release.distribution.architectures:
                        release.distribution.architectures.append(result.arch)
                    if not result.component in release.distribution.components:
                        release.distribution.components.append(result.component)
                    if not result.section in release.distribution.sections:
                        release.distribution.sections.append(result.section)

                    # Create symlink
                    dists_path = os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), result.component.name))
                    if result.type.name == 'deb':
                        dists_path += os.sep + "binary-" + result.arch.name
                    elif result.type.name == 'dsc':
                        dists_path += os.sep + "source"
                    if not os.path.exists(dists_path):
                        os.makedirs(dists_path)
                    current_dir = os.getcwd()
                    os.chdir(dists_path)
                    for file in result.files:
                        if os.path.exists(file.name):
                            os.unlink(file.name)
                        os.symlink(os.path.relpath(pool_path + os.sep + file.name), file.name)
                    os.chdir(current_dir)
                    self._updateInventory(session, release=release, distribution=distribution)
        return result

    def removePackage(self, session, package, arch=None, release=None, distribution=None):
        result = False

        if isinstance(arch, (str, unicode)):
            arch = self._getArchitecture(session, arch)

        if isinstance(package, (str, unicode)) and arch is None:
            for p in self._getPackages(session, package):
                self.env.log.debug("Trying to remove Package %s with Architecture %s" % (p.name, p.arch))
                self.removePackage(session, p, arch = p.arch, release=release, distribution=distribution)
        elif isinstance(package, (str, unicode)):
            package = self._getPackage(session, package, arch=arch)

        if isinstance(release, (str, unicode)):
            release = self._getRelease(session, release)

        if isinstance(distribution, (str, unicode)):
            distribution = self._getDistribution(session, distribution)

        if package is not None:
            if release is not None:
                if package in release.packages[:]:
                    dists_path = os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), package.component.name))
                    if package.type.name == 'deb':
                        dists_path += os.sep + "binary-" + package.arch.name
                    elif package.type.name == 'dsc':
                        dists_path += os.sep + "source"
                    else:
                        raise ValueError(N_("Unknown package type {type}").format(type=package.type.name))
                    for file in package.files:
                        if os.path.exists(dists_path + os.sep + file.name):
                            try:
                                os.unlink(dists_path + os.sep + file.name)
                            except:
                                self.env.log.error("Could not remove file %s" % dists_path + os.sep + file.name)
                                raise
                        else:
                            self.env.log.error("Strange: %s does not exist!" % dists_path + os.sep + file.name)
                    release.packages.remove(package)
                    self._updateInventory(session, release=release)
                    result = True

                    pool_path = os.sep.join((release.distribution.repository.path, "pool", release.distribution.type.name, package.component.name))
                    rollback_path = os.sep.join((release.distribution.repository.path, "rollback", release.distribution.type.name, package.component.name))
                    if not self.env.config.getOption('rollback', section = 'repository')==False and not os.path.exists(rollback_path):
                        os.makedirs(rollback_path)
                    try:
                        # Move package to rollback pool, remove row if no release is linked
                        if not package.releases:
                            if package.name.startswith('lib'):
                                pool_path += os.sep + str(package.name).lower()[:3]
                            else:
                                pool_path += os.sep + str(package.name).lower()[0]
                                pool_path += os.sep + package.name.lower()
                            for file in package.files:
                                package_path = pool_path + os.sep + file.name
                                if os.path.exists(package_path):
                                    if not self.env.config.getOption('rollback', section = 'repository')==False:
                                        shutil.move(package_path, rollback_path + os.sep + file.name)
                                    else:
                                        os.unlink(package_path)  # Remove package file
                            session.delete(package)
                    except:
                        self.env.log.error("Could not remove file %s" % package_path)
                        raise

                    try:
                        os.removedirs(pool_path) # Remove leaf dirs
                    except OSError:
                        pass
                    except:
                        raise

            elif distribution is not None:
                if distribution.releases:
                    result = True
                for release in distribution.releases:
                    self.removePackage(session, package, release=release)
            else:
                distributions = []
                if package.releases is not None:
                    for release in package.releases:
                        if release.distribution not in distributions:
                            distributions.append(release.distribution)

                if distributions:
                    result = True
                for distribution in distributions:
                    result &= self.removePackage(session, package, distribution=distribution)

        return result


    def _getDistribution(self, session, name):
        try:
            result = session.query(DebianDistribution).filter_by(name=name).one()
        except:
            result = None
        return result

    def _getRelease(self, session, name):
        try:
            result = session.query(Release).filter_by(name=name).one()
        except:
            result = None
        return result

    def _getPackage(self, session, name, arch=None, version=None):
        try:
            result = session.query(DebianPackage).filter_by(name=name)
            if arch:
                result = result.filter_by(arch=arch)
            if version:
                result = result.filter_by(version=version)
            result = result.one()
        except:
            result = None
        self.env.log.debug("name = %s, arch = %s -> %s" % (name, arch, result))
        return result

    def _getPackages(self, session, name):
        try:
            result = session.query(DebianPackage).filter_by(name=name).all()
        except:
            result = None
        return result

    def _getPackageFromUrl(self, session, url, origin=None, component=None):
        result = None
        if url.endswith('.deb'):
            deb = debfile.DebFile(url)
            if 'Package' in deb.debcontrol():
                result = DebianPackage(deb.debcontrol().get("Package"))
                description = deb.debcontrol().get("Description").split('\n')
                result.description = description[0]
                result.long_description = string.join(map(lambda l: ' ' + l, description[1:]), '\n')
                result.version = deb.debcontrol().get("Version")
                result.maintainer = deb.debcontrol().get("Maintainer")
                result.section = self._getSection(session, deb.debcontrol().get("Section"), add=True)
                if component:
                    result.component = self._getComponent(session, component, add=True)
                else:
                    if "/" in deb.debcontrol().get("Section"):
                        result.component = self._getComponent(session, deb.debcontrol().get("Section").split("/")[0], add=True)
                    else:
                        result.component = self._getComponent(session, "main", add=True)
                result.arch = self._getArchitecture(session, deb.debcontrol().get("Architecture"), add=True)
                result.priority = self._getPriority(session, deb.debcontrol().get("Priority"), add=True)
                result.depends = deb.debcontrol().get("Depends")
                result.installed_size = deb.debcontrol().get("Installed-Size")
                result.recommends = deb.debcontrol().get("Recommends")
                result.suggests = deb.debcontrol().get("Suggests")
                result.provides = deb.debcontrol().get("Provides")
                result.files.append(self._getFile(session, url, add=True))
                result.type = self._getType(session, str(result.files[0].name).split('.')[-1], add=True)
            existing = self._getPackage(session, result.name, arch=result.arch, version=result.version)
            if existing is not None:
                result = existing
        elif url.endswith('.dsc'):
            c = deb822.Dsc(open(url))
            if 'Source' in c:
                result = DebianPackage(c['Source'])
                result.arch = self._getArchitecture(session, 'source', add=True)
                result.version = c['Version']
                result.maintainer = c['Maintainer']
                result.build_depends = c['Build-Depends']
                result.standards_version = c['Standards-Version']
                result.files.append(self._getFile(session, url, add=True))
                result.type = self._getType(session, "dsc", add=True)
                if component:
                    result.component = self._getComponent(session, component,
                                                          add=True)
            if origin is not None:
                base_url = origin[0:origin.rfind(os.path.basename(url))]
                download_dir = os.path.dirname(url)
                # Download additional files
                if origin.startswith(('http', 'ftp')):
                    if c.has_key('Files'):
                        for source_file in c['Files']:
                            request = urllib2.Request(base_url + source_file['name'])
                            try:
                                file = urllib2.urlopen(request)
                                local_file = open(download_dir + os.sep + source_file['name'], "w")
                                local_file.write(file.read())
                                local_file.close()
                                local_url = download_dir + os.sep + source_file['name']
                                checksum = str(source_file['md5sum'])
                                if not checksum == self._get_md5_for_file(local_url):
                                    raise Exception
                                result.files.append(self._getFile(session, local_url, add=True))
                            except urllib2.HTTPError, e:
                                print "HTTP Error:", e.code, url
                            except urllib2.URLError, e:
                                print "URL Error:", e.reason, url
                else:
                    download_dir = os.path.dirname(origin)
                    if c.has_key('Files'):
                        for source_file in c['Files']:
                            local_url = download_dir + os.sep + source_file['name']
                            if os.path.exists(local_url):
                                checksum = str(source_file['md5sum'])
                                if not checksum == self._get_md5_for_file(local_url):
                                    raise Exception
                                result.files.append(self._getFile(session, local_url, add=True))

                # We need to extract the source package to get the target section
                for file in result.files:
                    if file.name.endswith('.dsc'):
                        p = subprocess.Popen(
                        "LANG=C dpkg-source -x --no-check '%s'" % file.name,
                        shell=True,
                        stderr=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        cwd=download_dir)
                        unpack_result = os.waitpid(p.pid, 0)[1]
                        if unpack_result > 0:
                            self.env.log.error(p.stderr)
                            result = False
                        dir_name = None
                        for line in p.stdout:
                            if line.startswith("dpkg-source: info: extracting %s" % result.name):
                                dir_name = line[line.rfind(" ")+1:].strip()
                        p.stdout.close()
                        if os.path.exists(download_dir + os.sep + dir_name):
                            try:
                                f = open(os.sep.join((download_dir, dir_name, "debian", "control")), 'r')
                                for line in f:
                                    if line.startswith("Section:"):
                                        result.section = self._getSection(session, line[line.find(":")+1:].strip(), add=True)
                                        if component:
                                            result.component = self._getComponent(session, component, add=True)
                                        else:
                                            if "/" in result.section.name:
                                                result.component = self._getComponent(session, result.section.name.split("/")[0], add=True)
                                            else:
                                                result.component = self._getComponent(session, "main", add=True)
                                f.close()
                            except:
                                raise
        return result

    def _get_md5_for_file(self, filename, block_size=2**20):
        md5 = hashlib.md5()
        f = open(filename)
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        f.close()
        return md5.hexdigest()

    def _getPriority(self, session, name, add=False):
        result = None
        try:
            result = session.query(DebianPriority).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = DebianPriority(name)
                session.add(result)
        return result

    def _getComponent(self, session, name, add=False):
        result = None
        try:
            result = session.query(Component).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Component(name)
                session.add(result)
        return result

    def _getSection(self, session, name, add=False):
        result = None
        try:
            result = session.query(Section).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Section(name)
                session.add(result)
        return result

    def _getArchitecture(self, session, name, add=False):
        result = None
        try:
            result = session.query(Architecture).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Architecture(name)
                session.add(result)
        return result

    def _getFile(self, session, url, add=False):
        result = None
        try:
            result = session.query(File).filter_by(name=os.path.basename(url)).one()
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
                session.add(result)
        return result

    def _getType(self, session, name, add=False):
        result = None
        try:
            result = session.query(Type).filter_by(name=name).one()
        except NoResultFound:
            if add:
                result = Type(name)
                session.add(result)
        return result

    def _getGPGEnvironment(self, session):
        result = None
        work_dir = tempfile.mkdtemp()
        repository = session.query(Repository).filter_by(path=self.env.config.getOption('path', section = 'repository')).one()
        gpg = gnupg.GPG(gnupghome=work_dir)
        if not repository.keyring:
            self.env.log.debug("Generating GPG Key")
            input_data = gpg.gen_key_input(key_type="RSA", key_length=1024)
            key = gpg.gen_key(input_data)
            repository.keyring = Keyring(name=key.fingerprint, data=gpg.export_keys(key, True))
            self.env.log.debug("Exported key '%s' to repository" % key)
        else:
            gpg.import_keys(repository.keyring.data)
            self.env.log.debug("Using existing secret key '%s'" % repository.keyring.name)
        result = work_dir
        return result

    def _signFile(self, session, filename):
        result = False
        if os.path.exists(filename):
            try:
                work_dir = self._getGPGEnvironment(session)
                gpg = gnupg.GPG(gnupghome=work_dir)
                stream = open(filename, 'rb')
                signed_ascii_data = str(gpg.sign_file(stream))
                stream.close()

                sign_file = open(filename+".gpg", 'wb')
                sign_file.write(signed_ascii_data)
                sign_file.close()

                shutil.rmtree(work_dir)
                result = True
            except:
                raise
        return result

    def _updateInventory(self, session, release=None, distribution=None):
        result = True
        if release:
            if isinstance(release, (str, unicode)):
                release = self._getRelease(session, release)

            release._initDirs()
            # Create Packages.gz and Packages.bz2
            for component in release.distribution.components:
                for architecture in release.distribution.architectures:
                    if architecture.name == 'source':
                        p = subprocess.Popen(
                            "dpkg-scansources . > Sources",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, architecture.name)))
                        packages_result = os.waitpid(p.pid, 0)[1]
                        if packages_result > 0:
                            self.env.log.error(p.stderr)
                            result = False
                        p = subprocess.Popen(
                            "gzip -c Sources > Sources.gz",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, architecture.name)))
                        packages_result = os.waitpid(p.pid, 0)[1]
                        if packages_result > 0:
                            self.env.log.error(p.stderr)
                            result = False
                        p = subprocess.Popen(
                            "bzip2 -c Sources > Sources.bz2",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, architecture.name)))
                        packages_result = os.waitpid(p.pid, 0)[1]
                        if packages_result > 0:
                            self.env.log.error(p.stderr)
                            result = False
                    else:
                        p = subprocess.Popen(
                            "dpkg-scanpackages . > Packages",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, 'binary-' + architecture.name)))
                        packages_result = os.waitpid(p.pid, 0)[1]
                        if packages_result > 0:
                            self.env.log.error(p.stderr)
                            result = False

                        p = subprocess.Popen(
                            "gzip -c Packages > Packages.gz",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, 'binary-' + architecture.name)))
                        gzip_result = os.waitpid(p.pid, 0)[1]
                        if gzip_result > 0:
                            self.env.log.error(p.stderr)
                            result = False

                        p = subprocess.Popen(
                            "bzip2 -c Packages > Packages.bz2",
                            shell=True,
                            stderr=subprocess.PIPE,
                            cwd=os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), component.name, 'binary-' + architecture.name)))
                        bzip_result = os.waitpid(p.pid, 0)[1]
                        if bzip_result > 0:
                            self.env.log.error(p.stderr)
                            result = False

            # Create Release files
            p = subprocess.Popen(
                "apt-ftparchive -qq -o 'APT::FTPArchive::Release::Suite=%s' -o 'APT::FTPArchive::Release::Codename=%s' release . > Release" % (release.name, release.codename if release.codename is not None else release.name),
                shell=True,
                stderr=subprocess.PIPE,
                cwd = os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep))))
            release_result = os.waitpid(p.pid, 0)[1]
            if release_result > 0:
                self.env.log.error(p.stderr)
                result = False

            if os.path.exists(os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), "Release"))):
                signature = self._signFile(session, os.sep.join((release.distribution.path, "dists",  release.name.replace('/', os.sep), "Release")))

            for child in release.children:
                result = result and self._updateInventory(session, release = child.name)
        elif distribution:
            if isinstance(distribution, (str, unicode)):
                distribution = self._getDistribution(session, distribution)

            for release in distribution.releases:
                result = result and self._updateInventory(session, release = release)

        return result

    def renameRelease(self, session, source, target):
        result = False
        source_path = os.sep.join((source.distribution.repository.path, source.distribution.name, "dists", source.name.replace('/', os.sep)))
        try:
            source._rename(target)
            result = self._updateInventory(session, release=target)
            if not result:
                self.env.log.error("Updating inventory for release '%s' failed!" % target)
            if os.path.exists(source_path):
                shutil.rmtree(source_path)
            result = True
        except:
            self.env.log.error("Caught unknown exception %s" % sys.exc_info()[0])
            raise
            result = False
        return result
