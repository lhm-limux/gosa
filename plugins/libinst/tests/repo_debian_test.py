# -*- coding: utf-8 -*-
import unittest

from sqlalchemy.orm import sessionmaker
from libinst.manage import RepositoryManager
from libinst.repository import Type
from gosa.common.env import Environment
import pprint

class TestDebianRepository(unittest.TestCase):

    env = None

    def setUp(self):
        """ Stuff to be run before every test """
        Environment.config = "test-libinst.conf"
        Environment.noargs = True
        self.env = Environment.getInstance()
        self.mgr = RepositoryManager()
        engine = self.env.getDatabaseEngine("repository")
        self._session = self.mgr.getSession()

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
        self.assertTrue(self.mgr.addKeys(keyring))

        self.helperAddRepositoryTypes()
        self.assertTrue(self.mgr.createDistribution("debian", "deb"))
        self.assertTrue(self.mgr.createRelease("debian", "lenny"))
        self.assertTrue(self.mgr.createRelease("debian", "lenny/5.0.4"))
        self.assertTrue(self.mgr.createRelease("debian", "squeeze"))


    def tearDown(self):
        for distribution in self.mgr.getDistributions()[:]:
            self.mgr.removeDistribution(distribution['name'], recursive = True)


    def test_getRepositoryTypes(self):
        typelist = self.mgr.getRepositoryTypes()
        self.assertEquals(len(typelist), 3 )
        self.assertEquals(typelist["deb"], "Debian Package")
        self.assertEquals(typelist["msi"], "Windows MSI Package")
        self.assertEquals(typelist["rpm"], "Redhat Package")


    def test_createDistribution(self):
        distName = "python2.6"
        repoType = "deb"
        distUrl = "http://www.python.org/deb/python2.6.deb"
        #nicht unterstützter repotyp soll Exception werfen
        self.assertRaises(ValueError, self.mgr.createDistribution, distName, "Dumdidum", mirror=distUrl)
        self.assertRaises(ValueError, self.mgr.createDistribution, "", repoType, mirror="noUrl")
        self.assertRaises(ValueError, self.mgr.createDistribution, None, repoType, mirror="noUrl")
        self.assertTrue(self.mgr.createDistribution(distName, repoType, mirror=distUrl))


    def test_getMirrorURL(self):
        release = "lenny/5.0.4"
        self.assertEquals("http://localhost/repository/debian/" + release, self.mgr.getMirrorURL(release))

    def test_getMirrorURL2(self):
        release = "debian/lenny/5.0.4"
        self.assertEquals("http://localhost/repository/" + release, self.mgr.getMirrorURL(release))

    def test_getMirrorURL3(self):
        release = "invalid/lenny/5.0.4"
        self.assertRaises(ValueError, self.mgr.getMirrorURL, release)

    def test_getDistributions(self):
        distList = self.mgr.getDistributions()
        self.assertEquals(len(distList), 1)


    def test_removeDistribution(self):
        distName = "python2.6"
        repoType = "deb"
        distUrl = "http://www.python.org/deb/python2.6.deb"
        before = self.mgr.getDistributions()
        self.assertTrue(self.mgr.createDistribution(distName, repoType, mirror=distUrl))
        self.assertTrue(self.mgr.removeDistribution(distName, recursive=True))
        after = self.mgr.getDistributions()
        self.env.log.debug(after)
        self.assertEquals(len(before), len(after))


    def test_createRelease(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildRelease1stLevel(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/4.0.1"))
        self.assertTrue("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildRelease1stLevelFail(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertRaises(ValueError, self.mgr.createRelease, "debian", "etch/4.0.1")
        self.assertFalse("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildReleaseDuplicateName(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertFalse("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/etch"))
        self.assertTrue("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildReleaseDuplicateNameWithRemoval(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/etch"))
        self.assertTrue("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.removeRelease("etch/etch"))
        self.assertFalse("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildReleaseDuplicateNameWithRename(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/etch"))
        self.assertTrue("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.renameRelease("etch", "etch2"))
        self.assertTrue("etch2" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue("etch2/etch" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildReleaseDuplicateNameWithRename2(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/etch"))
        self.assertTrue("etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/etch/etch"))
        self.assertTrue("etch/etch/etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.renameRelease("etch/etch", "etch/etch2"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue("etch/etch2" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue("etch/etch2/etch" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildRelease3rdLevel(self):
        self.assertFalse("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch"))
        self.assertTrue("etch" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/4.0.1"))
        self.assertTrue("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/4.0.1/prod" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertTrue(self.mgr.createRelease("debian", "etch/4.0.1/prod"))
        self.assertTrue("etch/4.0.1/prod" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_createChildRelease3rdLevelFail(self):
        self.assertFalse("etch/4.0.1" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertFalse("etch/4.0.1/prod" in [r['name'] for r in self.mgr.getReleases("debian")])
        self.assertRaises(ValueError, self.mgr.createRelease, "debian", "etch/4.0.1/prod")
        self.assertFalse("etch/4.0.1/prod" in [r['name'] for r in self.mgr.getReleases("debian")])


    def test_releaseNameFail(self):
        self.assertRaises(ValueError, self.mgr.createRelease, "debian", "lenny+")
        self.assertRaises(ValueError, self.mgr.createRelease, "debian", "master")


    def test_DistributionNameFail(self):
        self.assertRaises(ValueError, self.mgr.createDistribution, "debian+", "deb")
        self.assertRaises(ValueError, self.mgr.createDistribution, "master", "deb")


    def test_getReleases(self):
        self.assertEquals(len(self.mgr.getReleases("debian")), 3)


    def test_getArchitectures(self):
        self.assertEquals(len(self.mgr.getArchitectures()), 0)
        self.assertTrue(self.mgr.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
        self.assertEquals(len(self.mgr.getArchitectures()), 1)


    def test_getSections(self):
        self.assertEquals(len(self.mgr.getSections()), 0)
        self.assertTrue(self.mgr.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
        self.assertEquals(len(self.mgr.getSections()), 1)


    def test_removeRelease(self):
        before = self.mgr.getReleases()
        self.assertTrue(self.mgr.createRelease("debian", "lenny_test"))
        self.assertEquals(len(before), len(self.mgr.getReleases())-1)
        self.assertTrue(self.mgr.removeRelease("lenny_test"))
        self.assertEquals(len(before), len(self.mgr.getReleases()))


    def test_renameRelease(self):
        self.assertTrue(self.mgr.createRelease("debian", "lenny_test"))
        self.assertFalse(self.mgr._getRelease("openlenny"))
        self.assertTrue(self.mgr.renameRelease("lenny_test", "openlenny"))
        self.assertTrue(self.mgr._getRelease("openlenny"))
        self.assertFalse(self.mgr._getRelease("lenny_test"))


    def test_parentReleaseInheriting(self):
        self.assertFalse("kalign" in [p['name'] for p in self.mgr.getPackages(release = "lenny")])
        self.assertTrue(self.mgr.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
        self.assertTrue("kalign" in [p['name'] for p in self.mgr.getPackages(release = "lenny")])
        self.assertTrue(self.mgr.createRelease("debian", "lenny/5.0.5"))
        self.assertTrue("kalign" in [p['name'] for p in self.mgr.getPackages(release = "lenny/5.0.5")])


    def test_addSourcePackage(self):
        self.assertFalse("jaaa" in [p['name'] for p in self.mgr.getPackages(release = "lenny", arch="source")])
        self.assertTrue(self.mgr.addPackage("http://ftp.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1.dsc", release = "lenny"))
        self.assertTrue("jaaa" in [p['name'] for p in self.mgr.getPackages(release = "lenny", arch="source")])


    def test_removeSourcePackage(self):
        self.assertFalse("jaaa" in [p['name'] for p in self.mgr.getPackages(release = "lenny", arch="source")])
        self.assertTrue(self.mgr.addPackage("http://ftp.de.debian.org/debian/pool/main/j/jaaa/jaaa_0.4.2-1.dsc", release = "lenny"))
        self.assertTrue("jaaa" in [p['name'] for p in self.mgr.getPackages(release = "lenny", arch="source")])
        self.assertTrue(self.mgr.removePackage("jaaa", release = "lenny", arch="source"))
        self.assertFalse("jaaa" in [p['name'] for p in self.mgr.getPackages(release = "lenny", arch="source")])


    def test_createMirror(self):
        pass


    def test_removeMirror(self):
        pass


    def test_addChannel(self):
        pass


    def test_removeChannel(self):
        pass


    def test_getPackages(self):
        pass


    def test_getPackagesInformation(self):
        pass


    def test_getPackageInformation(self):
        pass


    def test_addDistribution(self):
        self.assertTrue(self.mgr.createDistribution("debian_test", "deb"))


    def test_addPackage(self):
        self.assertTrue(self.mgr.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
        self.assertTrue("kalign" in [p['name'] for p in self.mgr.getPackages(release = "lenny")])


    def test_removePackage(self):
        before = self.mgr.getPackages(release = "lenny")
        self.assertTrue(self.mgr.addPackage("http://ftp2.de.debian.org/debian/pool/main/k/kalign/kalign_2.03-2_i386.deb", release = "lenny"))
        after = self.mgr.getPackages(release = "lenny")
        self.assertEquals(len(before), len(after) - 1)
        self.assertTrue(self.mgr.removePackage("kalign", release = "lenny"))
        self.assertEquals(len(before), len(self.mgr.getPackages(release = "lenny")))


    def helperAddRepositoryTypes(self):
        deb = Type("deb", description = "Debian Package")
        rpm = Type("rpm", description = "Redhat Package")
        msi = Type("msi", description = "Windows MSI Package")
        self._session.add_all([deb,rpm,msi])
        self._session.commit()


if __name__ == '__main__':
    unittest.main()
