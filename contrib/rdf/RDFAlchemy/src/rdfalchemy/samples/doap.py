from rdfalchemy import rdfSubject, rdfSingle, rdfMultiple
from rdfalchemy.orm import mapper
from rdflib import Namespace

from rdfalchemy.samples.foaf import Person

DOAP=Namespace("http://usefulinc.com/ns/doap#")
FOAF=Namespace("http://xmlns.com/foaf/0.1/" )

class Project(rdfSubject):
    rdf_type = DOAP.Project
    name       = rdfSingle(DOAP.name)
    created    = rdfSingle(DOAP.created)
    homepage   = rdfSingle(DOAP.homepage)
    shortdesc  = rdfMultiple(DOAP.shortdesc)
    releases   = rdfMultiple(DOAP.release, range_type=DOAP.Version)
    language   = rdfSingle(DOAP['programming-language']) # because of the hyphen, we can't use DOAP.programming-language
    maintainer = rdfSingle(DOAP.maintainer,range_type=FOAF.Person)


class Release(rdfSubject):
    rdf_type = DOAP.Version
    name = rdfSingle(DOAP.revision)
    created = rdfSingle(DOAP.created)
    shortdesc = rdfMultiple(DOAP.shortdesc)
    file_releases = rdfMultiple(DOAP['file-release'])

# mapper()
# The above line works becuase * is implied
# The below line is just more explicit
mapper(Project,Release, Person)

def show_project(p):
    print "\n============================"
    print "Name is %s" % p.name
    print "  created on %s" % p.created
    # bacause of `mapper()`, release below will be an instance of Release 
    # so we can use dot notation on it
    for release in p.releases:
        print "  %s released on %s" % (release.name,release.created)
        for f in release.file_releases:
            print "    with file %s" % f.resUri # or f.n3()
    

if __name__ == '__main__':
    loads=["http://doapspace.org/doap/sf/accs.rdf","http://doapspace.org/doap/sf/nut"]
    for url in loads:
        rdfSubject.db.load(url)
        
    for p in Project.ClassInstances():
        show_project(p)
        
    # A Place to gather more doap records
    pypirss="http://pypi.python.org/pypi?%3Aaction=rss"
