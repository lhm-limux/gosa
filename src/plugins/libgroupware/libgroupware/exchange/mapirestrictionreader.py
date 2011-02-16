# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: mapirestrictionreader.py 1370 2010-11-16 14:03:29Z breucking $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
from win32com.mapi import mapitags

class MapiRestrictionReader():

    @staticmethod
    def getFilter(restriction):
        if restriction == None:
            return "AND", None
        #isAndRestriction
        if len(restriction) == 0:
            return "AND", []
        elif len(restriction) == 2:
            #Decompose Restriction
            if (restriction[0] == mapitags.RES_AND):
                type = "AND"
            elif (restriction[0] == mapitags.RES_OR):
                type = "OR"
            else:
                raise GroupwareValueError(
                    N_("Received unsupported condition from MAPI"))
            
            filters = MapiRestrictionReader._decomposeFilters(restriction[1])
            
            return type, filters
        else:
            raise GroupwareValueError(
                N_("Received unsupported condition from MAPI"))
    
    @staticmethod
    def _decomposeFilters(sRestrictionArray):
        filters = []
        for restriction in sRestrictionArray:
            #print restriction
            if MapiRestrictionReader._isSubjectRestriction(restriction):
                comperator = MapiRestrictionReader._getComperator( \
                    restriction[1][0])
                gosaFilter = {'FIELD': 'subject', \
                    "COMPARATOR": comperator, "VALUE": restriction[1][2][1]}
                filters.append(gosaFilter)
            elif MapiRestrictionReader._isNotSubjectRestriction(restriction):
                comperator = MapiRestrictionReader._getComperator( \
                    restriction[1][1][0])
                gosaFilter = {'FIELD': 'subject', \
                    "COMPARATOR": comperator + " not", "VALUE": \
                    restriction[1][1][2][1]}
                filters.append(gosaFilter)
            elif MapiRestrictionReader._isSizeRestriction(restriction):
                comperator = MapiRestrictionReader._getComperator( \
                    restriction[1][0])
                gosaFilter = {'FIELD': 'size', \
                    "COMPARATOR": comperator, "VALUE": \
                    restriction[1][2][1]}
                filters.append(gosaFilter)
            elif (MapiRestrictionReader._isDateRestriction(restriction)):
                
                r1 = restriction[1][0][1]
                r2 = restriction[1][1][1]
                
                if (r1[0] == mapitags.RELOP_GT and r2[0] == mapitags.RELOP_LT):
                    comperator = "greater than"
                    value = restriction[1][0][1][2][1]
                elif (r1[0] == mapitags.RELOP_LT and r2[0] == mapitags.RELOP_GT):
                    comperator = "less than"
                    value = restriction[1][1][1][2][1]
                else:
                    raise GroupwareValueError(
                        N_("Received unsupported condition from MAPI"))
                gosaFilter = {'FIELD': 'date', \
                    "COMPARATOR": comperator, "VALUE": value}
                filters.append(gosaFilter)
            elif MapiRestrictionReader._isBodyRestriction(restriction):
                comperator = MapiRestrictionReader._getComperator( \
                    restriction[1][0])
                gosaFilter = {'FIELD': 'body', \
                    "COMPARATOR": comperator, "VALUE": restriction[1][2][1]}
                filters.append(gosaFilter)
            else:
                print "MYDEBUG: ", restriction
                raise GroupwareValueError(
                    N_("Received unsupported condition from MAPI"))
        return filters
            
    @staticmethod
    def _getComperator(mapiTag):
        if (mapiTag == mapitags.FL_FULLSTRING| mapitags.FL_IGNORECASE):
            return "is"
        if (mapiTag == mapitags.FL_SUBSTRING | mapitags.FL_IGNORECASE):
            return "contains"
        if (mapiTag == mapitags.RELOP_LT): return "less than"
        if (mapiTag == mapitags.RELOP_GT): return "greater than"
        if (mapiTag == mapitags.RELOP_EQ): return "equals"
        raise GroupwareValueError(
            N_("Received unsupported comperator from MAPI"))
       
    @staticmethod
    def _isDateRestriction(restriction):
        return restriction[0] == mapitags.RES_AND \
            and restriction[1][0][0] == mapitags.RES_PROPERTY \
            and restriction[1][1][0] == mapitags.RES_PROPERTY \
            and restriction[1][0][1][1] == mapitags.PR_MESSAGE_DELIVERY_TIME \
            and restriction[1][1][1][1] == mapitags.PR_MESSAGE_DELIVERY_TIME
            
    @staticmethod
    def _isSubjectRestriction(restriction):
        #print "??> ", restriction
        return restriction[0] == mapitags.RES_CONTENT \
            and restriction[1][1] == mapitags.PR_SUBJECT_W
            
    @staticmethod
    def _isSizeRestriction(restriction):
        return restriction[0] == mapitags.RES_PROPERTY \
            and restriction[1][1] == mapitags.PR_MESSAGE_SIZE_EXTENDED
            
    @staticmethod
    def _isNotSubjectRestriction(restriction):
        return restriction[0] == mapitags.RES_NOT \
            and restriction[1][1][1] == mapitags.PR_SUBJECT_W
            
    @staticmethod
    def _isBodyRestriction(restriction):
        return restriction[0] == mapitags.RES_CONTENT \
                and (
                    restriction[1][1] == mapitags.PR_BODY
                    or
                    restriction[1][1] == mapitags.PR_BODY_W
                    or
                    restriction[1][1] == mapitags.PR_BODY_A
                )