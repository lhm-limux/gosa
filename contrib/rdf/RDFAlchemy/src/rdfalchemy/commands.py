from paste.script.command import Command, BadCommand
import sys
from rdfalchemy import  rdfSubject, RDF, RDFS, Namespace, URIRef
from rdfalchemy.rdfsSubject import rdfsSubject, rdfsClass

OWL = Namespace("http://www.w3.org/2002/07/owl#")


class rdfSubjectCommand(Command):
    """Create an rdfSubject subclass with descriptors from an RDF Schema

    will set the rdf_type
    Descriptors will be created
    
      1.  rdfs:domain and rdfs:range are respected
      2.  rdfSingle is used for properties that are
            * owl:InverseFunctionalProperty
            * owl:FunctionalProperty   
      3.  rdfList or rdfContainer is used if the proper range is set
      4.  rdfMultiple is used for all others
      
    The resulting .py file is ment to be a skeleton for the developers confvience.  
    Do not expect to be able to use the raw results.
    """
    summary = __doc__.splitlines()[0]
    usage = '\npaster %s\n%s' % (__name__, __doc__)

    min_args = 0
    max_args = 1
    group_name = 'rdfalchemy'
    
    parser = Command.standard_parser(simulate=True)
    parser.add_option('-s','--schema',help='file name or url of rdfSchema for this class')
    parser.add_option('-o','--fout',help='output file name default: stdout (e.g. ../MyRdfModel.py)')
    parser.add_option('-l','--list', action='store_true', help='list valid instances of `owl:Class` in the schema file')    

    def command(self):
        """Main command to create controller"""
        try:
            if self.options.schema:
                ext = self.options.schema.split('.')[-1]
                ext = ext in ['n3','nt'] and ext or 'xml'
                print "rdfSubject.db.load('%s',format='%s')" % (self.options.schema, ext)
                rdfSubject.db.load(self.options.schema,format=ext)
            else:
                raise NotImplementedError('Need to pass in the schema No default yet')
                    
            choices  = filter(lambda x: isinstance(x, URIRef), rdfSubject.db.subjects(RDF.type, RDFS.Class))
            choices += filter(lambda x: isinstance(x, URIRef), rdfSubject.db.subjects(RDF.type, OWL.Class))
            choices  = filter(lambda x: not rdfSubject.db.qname(x).startswith('_'), choices)
            choices.sort()
            
            print "qnames that you can import from this schema:"
            for i, n in enumerate(choices):
                print "\t[%i] %s" % (i+1,rdfSubject.db.qname(n))
                
            if self.options.list:
                return
            
            name = self.challenge('Enter (a)ll,(q)uit or the number ot build for','q')
            if name.startswith('q'):
                return
            elif name.startswith('a'):
                raise NotImplementedError("(a)ll option not implented yet")
            else:
                try:
                    name = choices[int(name)-1]
                except Exception, e:
                    raise e

            c = rdfsClass("<%s>"%name)

            output = self.options.fout and file(self.options.fout,'w') or sys.stdout                
            print >>output, c._emit_rdfSubject()
                
            # Setup the controller
        except BadCommand, e:
            raise BadCommand('An error occurred. %s' % e)
        except:
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error occurred. %s' % msg)
