# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: mapirestrictionfactory.py 1370 2010-11-16 14:03:29Z breucking $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
from win32com.mapi import mapitags

class MapiRestrictionFactory():

    @staticmethod
    def createRestriction(type, conditions):

        restrictions = []
        if conditions is not None:
            for condition in conditions:
                if condition['FIELD'] == 'subject':
                    restrictions.append( \
                        MapiRestrictionFactory._createSubjectRestriction( \
                            condition))
                elif condition['FIELD'] == 'body':
                    restrictions.append( \
                        MapiRestrictionFactory._createBodyRestriction( \
                            condition))
                elif condition['FIELD'] == 'size':
                    restrictions.append( \
                        MapiRestrictionFactory._createSizeRestriction( \
                            condition))
                elif condition['FIELD'] == 'from':
                    restrictions.append( \
                        MapiRestrictionFactory._createFromRestriction( \
                            condition))
                elif condition['FIELD'] == 'date':
                    restrictions.append( \
                        MapiRestrictionFactory._createDateRestriction( \
                            condition))
                elif condition['FIELD'] == 'priority':
                    restrictions.append( \
                        MapiRestrictionFactory._createPriorityRestriction( \
                            condition))
                #elif condition['FIELD'] == 'to':
                #    restrictions.append( \
                #        MapiRestrictionFactory._createToRestriction( \
                #            condition))
                else:
                    raise GroupwareValueError(
                        N_("Invalid or unsupported condition FIELD value '%s'"),
                        str(condition['FIELD']))

        if type == 'AND': #AND
            baseRestriction = 0x0
        elif type == 'OR':
            baseRestriction = 0x1
        else:
            raise GroupwareValueError(
                N_("Invalid or unsupported TYPE value '%s'"),
                str(type))

        return [baseRestriction, restrictions]

    @staticmethod
    def _createSubjectRestriction(condition):
        if(condition['COMPARATOR']=='is' or \
            condition['COMPARATOR']=='equal'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))
        if(condition['COMPARATOR']=='is not' or \
            condition['COMPARATOR']=='not equal'):
            return (0x2, [(0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))])
        elif(condition['COMPARATOR']=='contains'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_SUBSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))
        elif(condition['COMPARATOR']=='contains not'):
            return (0x2, [(0x3, \
                (mapitags.FL_IGNORECASE | mapitags.FL_SUBSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))])
        elif(condition['COMPARATOR']=='is empty'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))
        elif(condition['COMPARATOR']=='is not empty'):
            return (0x2, [(0x3, \
                (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_SUBJECT_W, \
                    (mapitags.PR_SUBJECT_W, condition['VALUE'])))])
        else:
            raise GroupwareValueError, \
                ("Invalid/or unsupported Comaparator value" \
                + str(condition['COMPARATOR']))

    @staticmethod
    def _createBodyRestriction(condition):
        if(condition['COMPARATOR']=='is' or \
            condition['COMPARATOR']=='equal'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))
        if(condition['COMPARATOR']=='is not' or \
            condition['COMPARATOR']=='not equal'):
            return (0x2, [(0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))])
        elif(condition['COMPARATOR']=='contains'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_SUBSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))
        elif(condition['COMPARATOR']=='contains not'):
            return (0x2, [(0x3, \
                (mapitags.FL_IGNORECASE | mapitags.FL_SUBSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))])
        elif(condition['COMPARATOR']=='is empty'):
            return (0x3, (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))
        elif(condition['COMPARATOR']=='is not empty'):
            return (0x2, [(0x3, \
                (mapitags.FL_IGNORECASE | mapitags.FL_FULLSTRING, \
                mapitags.PR_BODY_W, \
                    (mapitags.PR_BODY_W, condition['VALUE'])))])
        else:
            raise GroupwareValueError, \
                ("Invalid/or unsupported Comaparator value" \
                + str(condition['COMPARATOR']))

    @staticmethod
    def _createSizeRestriction(condition):
        comperator = condition['COMPARATOR']
        if comperator == 'less than':
            operator = mapitags.RELOP_LT
        elif comperator == 'greater than':
            operator = mapitags.RELOP_GT
        elif comperator == 'is':
            operator = mapitags.RELOP_EQ
        else:
            raise GroupwareValueError(N_("Illegal size comperator '%s'"),\
                comperator)
        return (mapitags.RES_PROPERTY, (operator, \
            mapitags.PR_MESSAGE_SIZE_EXTENDED, (mapitags.PR_MESSAGE_SIZE_EXTENDED, condition['VALUE'])))
    
    @staticmethod
    def _createFromRestriction(condition):
        return (mapitags.RES_COMMENT, (0x00010001, \
            mapitags.PR_SENDER_EMAIL_ADDRESS, \
                (mapitags.PR_SENDER_EMAIL_ADDRESS, 'tester')))

    @staticmethod
    def _createPriorityRestriction(condition):
        comperator = condition['COMPARATOR']
        if comperator == 'less than':
            op = 0
        elif comperator == 'greater than':
            op = 2
        elif comperator == 'is':
            op = 4
        else: 
            raise GroupwareValueError(N_("Illegal size comperator '%s'"), \
                comperator)
        return (mapitags.RES_PROPERTY, (op, \
            mapitags.PR_IMPORTANCE, \
                (mapitags.PR_IMPORTANCE, condition['VALUE'])))

    @staticmethod
    def _createDateRestriction(condition):
        #start = datetime.fromtimestamp(0)
        #end = datetime.fromtimestamp(condition['VALUE'])
        comperator = condition['COMPARATOR']
        if comperator == 'less than':
            start = 0
            end = condition['VALUE']
        elif comperator == 'greater than':
            start = condition['VALUE']
            end = 2147483647 #Maximum Date
        else:
            raise GroupwareValueError(N_("Illegal date comperator '%s'"), comperator)

        propRestriction1 = (0x4, ( \
            mapitags.RELOP_GT, mapitags.PR_MESSAGE_DELIVERY_TIME, \
                (mapitags.PR_MESSAGE_DELIVERY_TIME, start)))
        propRestriction2 = (0x4, ( \
           mapitags.RELOP_LT, mapitags.PR_MESSAGE_DELIVERY_TIME, \
               (mapitags.PR_MESSAGE_DELIVERY_TIME, end)))

        andRrestriction = (mapitags.RES_AND, \
            [propRestriction1, propRestriction2])
        return andRrestriction

