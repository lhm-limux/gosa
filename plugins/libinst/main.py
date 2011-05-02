#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, shutil
from gosa.common.env import Environment
from libinst.manage import RepositoryManager

def main():
    Environment.config="libinst.conf"
    Environment.noargs=True
    env = Environment.getInstance()
    repo_path = env.config.getOption('path', section = 'repository')
    if os.path.exists(repo_path):
        print "Deleting path %s" % repo_path
        shutil.rmtree(repo_path)
    if os.path.exists(os.path.expanduser("~/repo")):
        shutil.rmtree(os.path.expanduser("~/repo"))
    if os.path.exists(os.path.expanduser("~/work")):
        shutil.rmtree(os.path.expanduser("~/work"))

    keyring = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.10 (GNU/Linux)

lQHYBEx2RJ8BBADGAvwUiutOLO+OgkpWmOfNczRcEWZSja8jfZJFAHkSknq7t9lM
FD0qYkjxnmGvi44cPmKu7Z2xkBxljyKK5pDOkCqB2QBUrXSnb3rg6/w9gX8Mh1er
e8VZ/45sjxqwoUIPWWsrmEotQ9388KbEhdw14FQj/rai/Xa7rqYI6nVQSQARAQAB
AAP6AyHggTljDsfnvu3ZQj/ihdj27A056XmOJ4elkobqNpfsdI9l8t3fy4dFvy28
8gKvnzG08uG1iyD1mnBho/sdytTKe7GMLDcHyWWBOl31WLKUzQFTOpQ6EjzKNyNl
CGvwSKBm8u81BfNi7FpfgnVI733jdqZ8Lvq5znKRrK4WJdECANOaZn78oghTONUQ
1Fo6PgrjFkD337TR3Dm5tllp0Mlly9C9/N5CiTZj/0VLNyzT0tHVik8WEmF37bgY
Zd2gA9kCAO+Oj6k9Bqs6uTjHFmT5NEGvoJVSd4Q+F4jDmT+U2yJEBUk1dHiRAcEr
NcRU5VMbpBk9rbsmikX0oA1gavaNmfECAJi9uX99nb+dNWpqFqHxuDKaHapG9cKv
AlI+btxIAzPFvqMuHMjFKn6T57D8QpIz1f7LdmlYKKOr3DRmaYOaJBClOrQ2QXV0
b2dlbmVyYXRlZCBLZXkgKEdlbmVyYXRlZCBieSBnbnVwZy5weSkgPGphbndAaG9t
ZXI+iLgEEwECACIFAkx2RJ8CGy8GCwkIBwMCBhUIAgkKCwQWAgMBAh4BAheAAAoJ
ELxLvnLaEqJwX2oD/2wAOYbZG68k7iDOqFI1TpQjlgRQKHNuvindjWrPjfgsDfZH
kEhidYX1IRzgyhhLjrPDcB0RTcnjlXm9xOXJb3tcuyKWxi2CHMstdgTMHt6xb37o
LcWMU6gayNYj7eMgCOFM6ywySRS81FC+PPnr147xbp5FwgmoPRK52MURsHJ+
=RwlJ
-----END PGP PRIVATE KEY BLOCK-----"""


    # Begin: New stuff
    manager = RepositoryManager()
    #print manager.getSupportedBaseInstallMethods()
    #print manager.getSupportedInstallMethods()

    manager.addKeys(keyring)
    #print "createDistribution:", manager.createDistribution("debian", "deb",
    #        {"mirror": "http://archive.debian.org/debian"},
    #        install_method="puppet")
    #print("getDistributions", manager.getDistributions())
    #print "createRelease:", manager.createRelease("debian", "test")
    #print("getDistributions", manager.getDistributions())
    #manager._getRelease("bo").distribution.architectures.append(manager._getArchitecture("i386", add=True))
    #manager.addMirrorProperty(distribution="debian", arch="i386", component="main")
    #manager.addMirrorProperty(distribution="debian", component="contrib")
    #manager.updateMirror(distribution="debian")
    ##manager._getRelease("bo").distribution.components.append(manager._getComponent("main", add=True))
    ##print("getDistributions", manager.getDistributions())
    #print(manager.getReleases({"distribution": "debian"}))
    ##manager._getRelease("bo").distribution._sync()
    ##print "createRelease:", manager.createRelease("debian", "lenny/1.0")
    #print "createRelease:", manager.createRelease("debian", "squeeze")
    #print("getReleases: distribution=debian", manager.getReleases(distribution="debian"))
    #print("addPackage: jaaa_0.4.2-1.dsc", manager.addPackage("http://ftp.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1.dsc", {"release": "lenny"}))
    #print("addPackage: kalign_2.03-2_i386.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
    #print("addPackage: kalign_2.03-2_i386.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "squeeze"))
    #print("addPackage: a2ps_4.14-1.1_i386.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/a/a2ps/a2ps_4.14-1.1_i386.deb", release = "lenny"))
    #print("addPackage: jaaa_0.4.2-1_amd64.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1_amd64.deb", {"release": "test"}))
    #print("addPackage: jaaa_0.4.2-1_amd64.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1_amd64.deb", release = "squeeze"))
    #print("getPackages: ", manager.getPackages(release="lenny", arch="i386", section="text"))
    #print("removePackage: jaaa", manager.removePackage("jaaa", release="lenny", arch="source"))
    #print("removePackage: kalign", manager.removePackage("kalign", release="lenny"))
    #print("removePackage: a2ps", manager.removePackage("a2ps"))
    #print("removePackage: jaaa", manager.removePackage("jaaa"))
    #print("addPackage: jaaa_0.6.0-1+b1_amd64.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.6.0-1+b1_amd64.deb", release = "lenny"))
    #print("addPackage: jaaa_0.4.2-1_amd64.deb", manager.addPackage("http://ftp2.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1_amd64.deb", release = "lenny"))
    #print(manager.getPackages())
    #print("createChildRelease", manager.createRelease("debian", "lenny/5.0.4"))
    #print("createChildRelease", manager.createRelease("debian", "lenny/lenny"))
    #print(manager.getReleases())
    #print("Packages for lenny:", manager.getPackages(release = 'lenny'))
    #print("Packages for lenny/5.0.4:", manager.getPackages(release = 'lenny/5.0.4'))
    #print("renameRelease:", manager.renameRelease("lenny", "openlenny"))
    #print(manager.getReleases())
    #print("Packages for lenny/5.0.4:", manager.getPackages(release = 'lenny/5.0.4'))
    #print("Packages for openlenny/5.0.4:", manager.getPackages(release = 'openlenny/5.0.4'))
    #print(manager.getArchitectures(release = "testing"))
    #print(manager.getArchitectures(distribution = "debian"))
    #print(manager.getArchitectures())
    #print(manager.getSections(release = "testing"))
    #print(manager.getSections(distribution = "debian"))
    #print(manager.getSections())
    #print(manager.getReleases(distribution = "debian"))
    #print(manager.getReleases())
    #print("removeRelease: ", manager.removeRelease(release = "bo"))
    #print("removeRelease: ", manager.removeRelease(release = "squeeze"))
    #print(manager.getReleases())
    #print(manager.listKeys())
    #print(manager.removeKey("BC4BBE72DA12A270"))
    #print(manager.listKeys())
    #print("getPackages: (lenny)", manager.getPackages(release='lenny'))
    #print("getPackages: (squeeze)", manager.getPackages(release='squeeze'))
    #print("getReleases: ", manager.getReleases("debian"))
    #print("in releaes", "squeeze" in [r.name for r in manager.getReleases("debian")])
    #print(manager.createDistribution("ubuntu", "deb"))
    #print("removeDistribution", manager.removeDistribution("debian", recursive=True))
    #print("removeDistribution", manager.removeDistribution("ubuntu"))
    #print("getDistributions", manager.getDistributions())

    # End:   New stuff


    exit(0)
    # session = Session()
    # section1 = Section('editors')
    # section2 = Section('shells')
    # session.add(section1)
    # session.add(section2)
    # arch1 = Architecture('i386')
    # arch2 = Architecture('x86_64')
    # arch3 = Architecture('source')
    # arch4 = Architecture('all')
    # session.add(arch1)
    # session.add(arch2)
    # session.add(arch3)
    # session.add(arch4)
    #
    # debian_type = Type('deb')
    # debian_type.description = "Debian Package"
    # type2 = Type('rpm')
    # type2.description = "Redhat Package"
    # type3 = Type('opsi')
    # type3.description = "Opsi Package"
    # session.add(debian_type)
    # session.add(type2)
    # session.add(type3)
    # session.add(type2)
    # session.add(type3)
    #
    # component1 = Component('main')
    # component2 = Component('contrib')
    # component3 = Component('non-free')
    # session.add(component1)
    # session.add(component2)
    # session.add(component3)
    #
    # priority_important = DebianPriority('important')
    # priority_optional = DebianPriority('optional')
    #
    # package1 = DebianPackage('bash')
    # package2 = DebianPackage('vim')
    # package1.arch = arch1
    # package2.arch = arch1
    # package1.type = type1
    # package2.type = type1
    # package1.component = component1
    # package2.component = component1
    # package1.section = section2
    # package2.section = section1
    # package1.priority = priority_optional
    # package2.priority = priority_important
    # session.add(package1)
    # session.add(package2)
    #
    #
    # distribution1 = Distribution('suse')
    # distribution2 = DebianDistribution('debian')
    # distribution3 = DebianDistribution('ubuntu')
    # session.add(distribution1)
    # session.add(distribution2)
    # session.add(distribution3)
    #
    # release1 = DebianRelease('lenny')
    # release1.packages.append(package1)
    # release1.packages.append(package2)
    #
    # release2 = Release('100oss')
    # release2.packages.append(package1)
    # release2.packages.append(package2)
    #
    # release3 = DebianRelease('lucid')
    # release3.packages.append(package1)
    # release3.packages.append(package2)
    #
    # session.add(release1)
    # session.add(release2)
    # session.add(release3)
    #
    # child_release = DebianRelease('5.0.4')
    # child_release.parent =  release1
    # session.add(child_release)
    #
    # distribution1.releases.append(release2)
    # distribution2.releases.append(release1)
    # distribution3.releases.append(release3)
    # distribution2.releases.append(child_release)
    # repository = Repository(name = 'archive.gonicus.de', path = repo_path)
    # session.add(repository)
    # repository.init_dirs()
    # session.commit()
    #
    # package_name= "hwinfo_15.20-2_i386.deb"
    # #package_hwinfo = debian_util.get_debian_package_from_file(package_name, session)
    # #session.merge(package_hwinfo)
    # debian_distribution = util.create_distribution('debian', session, type = 'deb')
    # repository.distributions.append(debian_distribution)
    # lenny_release = util.create_release('debian', 'lenny', session)
    # child_release = util.create_release('debian', '5', session, parent = 'lenny')
    # child_2_release = util.create_release('debian', '1', session, parent = '5')
    # child_3_release = util.create_release('debian', '3', session, parent = '1')
    # session.commit()
    # repository.init_dirs()
    # util.add_package(package_name, session, release = 'lenny')
    # session.commit()
    #
    # remote_package= "http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb"
    # util.add_package(remote_package, session, release = 'lenny')
    # util.add_package("http://ftp2.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1_amd64.deb", session, release = 'lenny')
    # util.add_package("http://ftp2.de.debian.org/debian/pool/main/i/iax/libiax0_0.2.2-8_i386.deb", session, release = 'lenny')
    # session.commit()
    #
    # util.update_inventory(session, distribution = 'debian')
    # util.get_packages(session, section = 'science')
    # print "Repository Types:", util.get_repository_types(session)
    # print "Distributions:", util.get_distributions(session)
    # print "Releases (instance):", util.get_releases(debian_distribution, session)
    # print "Releases (name):", util.get_releases('debian', session)
    # print "Architectures (instance):", util.get_architectures(debian_distribution, session)
    # print "Architectures (name):", util.get_architectures('debian', session)
    # print "Sections (instance):", util.get_sections(debian_distribution, session)
    # print "Sections (name):", util.get_sections('debian', session)
    # print "Packages (all):", util.get_packages(session)
    # print "Packages (Section 'science'):", util.get_packages(session, section = 'science')
    # print "Packages (Arch 'amd64' by name):", util.get_packages(session, arch = 'amd64')
    # print "Packages (Arch 'amd64' by instance):", util.get_packages(session, arch = util.get_architecture_from_name('amd64', session))
    #
    # ubuntu = util.create_distribution('ubuntu', session, type = 'deb', mirror = "http://de.archive.ubuntu.com/ubuntu")
    # ubuntu.architectures.append(util.get_architecture_from_name('i386', session))
    # ubuntu.architectures.append(util.get_architecture_from_name('amd64', session))
    # ubuntu.components.append(util.get_component_from_name('main', session))
    # lucid = util.create_release('ubuntu', 'lucid', session)
    # repository.distributions.append(ubuntu)
    # util.rename_release('lenny', 'testing', session)
    # session.commit()
    # #ubuntu.sync()

if __name__ == '__main__':
    main()
