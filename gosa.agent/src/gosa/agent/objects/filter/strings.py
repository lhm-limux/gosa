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
        if position == "right":
            new_val = map(lambda x: x + appstr, valDict[key]['value'] )
        else:
            new_val = map(lambda x: appstr + x, valDict[key]['value'] )
        valDict[key]['value'] = new_val
        return key, valDict

class Replace(ElementFilter):

    def __init__(self, obj):
        super(Replace, self).__init__(obj)

    def process(self, obj, key, valDict, regex, replacement):
        valDict[key]['value'] = map(lambda x: re.sub(regex, str(replacement), x), valDict[key]['value'])
        return key, valDict


class DateToString(ElementFilter):

    def __init__(self, obj):
        super(DateToString, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        valDict[key]['value'] = map(lambda x: x.strftime(fmt), valDict[key]['value'])
        return key, valDict


class TimeToString(DateToString):

    def __init__(self, obj):
        super(TimeToString, self).__init__(obj)


class StringToDate(ElementFilter):

    def __init__(self, obj):
        super(StringToDate, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        valDict[key]['value'] = map(lambda x: datetime.datetime.strptime(x, fmt).date(), valDict[key]['value'])
        return key, valDict


class StringToTime(ElementFilter):

    def __init__(self, obj):
        super(StringToTime, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        valDict[key]['value'] = map(lambda x: datetime.datetime.strptime(x, fmt), valDict[key]['value'])
        return key, valDict
