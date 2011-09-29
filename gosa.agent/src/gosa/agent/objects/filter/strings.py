# -*- coding: utf-8 -*-
import re
import datetime
from time import mktime
from gosa.agent.objects.filter import ElementFilter, ElementFilterException
import datetime

class ConcatString(ElementFilter):

    def __init__(self, obj):
        super(ConcatString, self).__init__(obj)

    def process(self, obj, key, valDict, appstr, position):
        if type(valDict[key]['value']) in [str, unicode]:
            if position == "right":
                new_val = valDict[key]['value'] + appstr
            else:
                new_val = appstr + valDict[key]['value']
            valDict[key]['value'] = new_val
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict

class Replace(ElementFilter):

    def __init__(self, obj):
        super(Replace, self).__init__(obj)

    def process(self, obj, key, valDict, regex, replacement):
        if type(valDict[key]['value']) in [str, unicode]:
            valDict[key]['value'] = re.sub(regex, str(replacement), valDict[key]['value'])
        else:
            raise ValueError("Unknown input type for filter %s. Type is '%s'!" % (
                    self.__class__.__name__, type(valDict[key]['value'])))

        return key, valDict


class DateToString(ElementFilter):

    def __init__(self, obj):
        super(DateToString, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        try:
            valDict[key]['value'] = valDict[key]['value'].strftime(fmt)
            valDict[key]['type'] = "String"
        except Exception as e:
            raise ElementFilterException("Failed to parse date-property value into 'string'! (%s:%s) %s" % (
                key, valDict[key]['value'], e))
        return key, valDict


class TimeToString(DateToString):

    def __init__(self, obj):
        super(TimeToString, self).__init__(obj)


class StringToDate(ElementFilter):

    def __init__(self, obj):
        super(StringToDate, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        try:
            valDict[key]['value'] = (datetime.datetime.strptime(valDict[key]['value'], fmt)).date()
            valDict[key]['type'] = datetime.date
        except Exception as e:
            raise ElementFilterException("Failed to parse string-property value into 'date' object! (%s:%s) %s" % (
                key, valDict[key]['value'], e))
        return key, valDict


class StringToTime(ElementFilter):

    def __init__(self, obj):
        super(StringToTime, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        try:
            valDict[key]['value'] = (datetime.datetime.strptime(valDict[key]['value'], fmt))
        except Exception as e:
            raise ElementFilterException("Failed to parse string-property value into 'date' object! (%s:%s) %s" % (
                key, valDict[key]['value'], e))
        return key, valDict
