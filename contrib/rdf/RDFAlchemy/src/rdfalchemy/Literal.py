#!/usr/bin/env python
# encoding: utf-8
"""
Literal.py

Created by Philip Cooper on 2008-02-09.
Copyright (c) 2008 Openvest. All rights reserved.
"""
from rdflib import Namespace, Literal
from rdflib.Literal import bind as bindLiteral
from rdflib.Literal import _PythonToXSD
import re
import logging

XSD = Namespace(u'http://www.w3.org/2001/XMLSchema#')

################################################################################
# Let's fix the logging.  This seems like a lot of work...
# all that it does is not log rebinding errors. 
# We know already about them ... and the warnings confuse the citizenry.
_log = logging.getLogger("rdflib")
if not _log.handlers:
    class rebindingLogFilter(logging.Filter):
        def filter(self, record):
            if record.getMessage().find("Rebinding") > -1:
                return False
            return True
    
    h = logging.StreamHandler()
    h.addFilter(rebindingLogFilter())
    _log.addHandler(h)
    
################################################################################
## Let's make toPython return a Decimal if an XSD.decimal in in the triplestore
try:
    from decimal import Decimal
    bindLiteral(XSD.decimal,Decimal)
    _PythonToXSD.update(dict([(Decimal,(str,XSD.decimal))]))
except AttributeError:
    ## rdflib2.4.1 changed  _PythonToXSD from a dict to a list
    _PythonToXSD.extend([(Decimal,(str,XSD.decimal))]) 
except:
    pass
    
################################################################################
## Default behavior returns untyped literals as literals
## this brings untyped literals back as unicode strings
bindLiteral(None,unicode)

################################################################################
## Default behavior returns string literals as literals
## this brings  string literals back as unicode strings
bindLiteral(XSD.string,unicode)
        
################################################################################
## Let's make toPython return a datetime if the literal has fractional seconds
## Note: dateparser adapted from http://www.mnot.net/python/isodate.py
## modified to: handle fractional seconds beyond tenths 
##              and to allow pseudo iso i.e. "2001-12-15 22:43:46" 
##                                        vs "2001-12-15T22:43:46"
import datetime

date_parser = re.compile(r"""^
    (?P<year>\d{4})
    (?:-
        (?P<month>\d{1,2})
        (?:-
            (?P<day>\d{1,2})
            (?:[T ]
                (?P<hour>\d{1,2})
                :
                (?P<minute>\d{1,2})
                (?::
                    (?P<second>\d{1,2})
                    (?P<dec_second>\.\d+)?
                )?                    
                (?:Z|(?:
                        (?P<tz_sign>[+-])
                        (?P<tz_hour>\d{1,2})
                        :?
                        (?P<tz_min>\d{2,2})
                     )
                )?
            )?
        )?
    )?
$""", re.VERBOSE)

def _strToDateTime(s):
        """ parse a string and return a datetime object. """
        assert isinstance(s, basestring)
        r = date_parser.search(s)
        try:
            a = r.groupdict('0')
        except:
            raise ValueError, 'invalid date string format'
            
        dt = datetime.datetime(int(a['year']),
                               int(a['month']) or 1,
                               int(a['day']) or 1,
                               # If not given these will default to 00:00:00.0
                               int(a['hour']),
                               int(a['minute']),
                               int(a['second']),
                               # Convert into microseconds
                               int(float(a['dec_second'])*1000000),
                               )
        tz_hours_offset = int(a['tz_hour'])
        tz_mins_offset = int(a['tz_min'])
        if a.get('tz_sign', '+') == "-":
            return dt + datetime.timedelta(hours = tz_hours_offset,
                                           minutes = tz_mins_offset)
        else:
            return dt - datetime.timedelta(hours = tz_hours_offset,
                                           minutes = tz_mins_offset)

bindLiteral(XSD.dateTime,_strToDateTime)
