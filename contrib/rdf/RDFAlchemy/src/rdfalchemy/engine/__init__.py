import os
import re
import urllib

def create_engine(url='', identifier="", create=False):
    """
    :returns: returns an open rdflib ConjunctiveGraph

    :param url: a string of the url
    :param identifier: URIRef of the default context for writing
    e.g.:
      
      - create_engine('mysql://myname@localhost/rdflibdb')
      - create_engine('sleepycat://~/working/rdf_db')
      - create_engine('zodb:///var/rdflib/Data.fs')
      - create_engine('zodb://localhost:8672')
      - create_engine('sesame://www.example.com:8080/openrdf-sesame/repositories/Test')      
      - create_engine('sparql://www.example.com:2020/sparql')            
    
    for zodb:
    
       the key in the Zope database is hardcoded as 'rdflib'
       urls ending in `.fs` indicate FileStorage
       otherwise ClientStoreage is assumed which requires
       a ZEO Server to be running"""
    if url=='' or url.startswith('IOMemory'):
        from rdflib import ConjunctiveGraph
        db = ConjunctiveGraph('IOMemory')
    elif url.lower().startswith('mysql://'):
        from rdflib import ConjunctiveGraph
        db = ConjunctiveGraph('MySQL',identifier)
        schema,opts = _parse_rfc1738_args(url)
        openstr= 'db=%(database)s,host=%(host)s,user=%(username)s'%opts
        if opts.get('password'):
            openstr += ',password=%(password)s' % opts
        if opts.get('port'):
            openstr += ',port=%(port)s' % opts
        db.open(openstr)
    elif url.lower().startswith('sleepycat://'):
        from rdflib import ConjunctiveGraph
        db = ConjunctiveGraph('Sleepycat',identifier=identifier)
        openstr = os.path.abspath(os.path.expanduser(url[12:]))
        db.open(openstr,create=create)
    elif url.lower().startswith('sqlite://'):
        from rdflib import ConjunctiveGraph
        db = ConjunctiveGraph('SQLite',identifier=identifier)
        openstr = os.path.abspath(os.path.expanduser(url[9:]))
        db.open(openstr,create=create)
    elif url.lower().startswith('zodb://'):
        import ZODB
        import transaction
        from rdflib import ConjunctiveGraph 
        db = ConjunctiveGraph('ZODB')
        if url.endswith('.fs'):
            from ZODB.FileStorage import FileStorage
            openstr = os.path.abspath(os.path.expanduser(url[7:]))
            if not os.path.exists(openstr) and not create:
                raise "File not found: %s"%openstr
            fs=FileStorage(openstr)
        else:
            from ZEO.ClientStorage import ClientStorage
            schema,opts = _parse_rfc1738_args(url)
            fs=ClientStorage((opts['host'],int(opts['port'])))
        # get the Zope Database
        zdb=ZODB.DB(fs)
        # open it
        conn=zdb.open()
        #get the root
        root=conn.root()
        # get the Conjunctive Graph
        if 'rdflib' not in root and create:
            root['rdflib'] = ConjunctiveGraph('ZODB')
        db=root['rdflib']
    elif url.lower().startswith('sesame://'):
        from rdfalchemy.sparql.sesame2 import SesameGraph
        db = SesameGraph("http://"+url[9:])
    elif url.lower().startswith('sparql://'):
        from rdfalchemy.sparql import SPARQLGraph
        db = SPARQLGraph("http://"+url[9:])
    else:
        raise "Could not parse  string '%s'" % url
    return db
    
def engine_from_config(configuration, prefix='rdfalchemy.', **kwargs):
    """Create a new Engine instance using a configuration dictionary.
    
    :param configuration: a dictionary, typically produced from a config file 
    where keys are prefixed, such as `rdfalchemy.dburi`, etc.  
    :param prefix: indicates the prefix to be searched for.
    
    """

    options = dict([(key[len(prefix):], configuration[key])
                 for key in configuration 
                  if key.startswith(prefix)])

    options.update(kwargs)
    url = options.pop('dburi')
    return create_engine(url, **options)

    
def _parse_rfc1738_args(name):
    """ parse url str into options
    code orig from sqlalchemy.engine.url """
    pattern = re.compile(r'''
            (\w+)://
            (?:
                ([^:/]*)
                (?::([^/]*))?
            @)?
            (?:
                ([^/:]*)
                (?::([^/]*))?
            )?
            (?:/(.*))?
            '''
            , re.X)

    m = pattern.match(name)
    if m is not None:
        (name, username, password, host, port, database) = m.group(1, 2, 3, 4, 5, 6)
        if database is not None:
            tokens = database.split(r"?", 2)
            database = tokens[0]
            query = (len(tokens) > 1 and dict( cgi.parse_qsl(tokens[1]) ) or None)
            if query is not None:
                query = dict([(k.encode('ascii'), query[k]) for k in query])
        else:
            query = None
        opts = {'username':username,'password':password,'host':host,'port':port,'database':database, 'query':query}
        if opts['password'] is not None:
            opts['password'] = urllib.unquote_plus(opts['password'])
        return (name, opts)
    else:
        raise exceptions.ValueError("Could not parse rfc1738 URL from string '%s'" % name)

