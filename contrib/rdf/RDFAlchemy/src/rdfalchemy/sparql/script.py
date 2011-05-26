#!/usr/bin/env python
# encoding: utf-8
"""
script.py

Created by Philip Cooper on 2008-04-29.
Copyright (c) 2008 Openvest. 
BSD License.
"""
from rdfalchemy.sparql import SPARQLGraph
from rdfalchemy import __version__
import sys
import re
import optparse


usage = 'usage: sparql [options] [endpointURL] query_file'
version = 'version: sparql '+__version__

optparser = optparse.OptionParser(usage=usage, version=version)
optparser.add_option('-q','--fin',help='Read query from file (defaults to stdin)')
optparser.add_option('-o','--fout',help='output file name (defaluts to stdout)')
optparser.add_option('-u','--url',help='url of the sparql endpoint')
optparser.add_option('-t','--format',type='choice',choices=['xml','json','brtr'],help="format to return one of: ['xml','json','brtr']")
optparser.set_defaults(format='xml')


# time echo "select * { ?s a ?o } limit 2" | sparql -t xml -u $SPARQL1 - | xsltproc xml-to-html.xsl -
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(url=None):
    
    try:
        output = ""
        
        try:
            opts, args = optparser.parse_args()
        except LookupError:
            optparser.print_help()
            

        if len(args) < 1:
            Usage('you must give at filename to read the query from..."-" signials stdin')
        elif len(args) > 2:
            Usage('too many args')
        
            
        fname = args[-1]
        if fname == '-':
            stream = sys.stdin
        else:
            stream = file(fname)
            
        query = stream.read()
        
        #output = opt.get.fileOut or sys.stdout
        if not opts.url:
            try:
                url =  re.search(r'(?:^|\n) *# *--url=([^ \s\n]+)',query).groups()[0]
            except:
                raise ValueError, "Need a url for the endpoint"
        else: 
            url = opts.url
        if not opts.fout:
            output = sys.stdout
        else:
            output = open(fout,"w")

        result = SPARQLGraph(url).query(query,resultMethod = opts.format ,rawResults=True)
        print >>output, result.read()

            
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())
