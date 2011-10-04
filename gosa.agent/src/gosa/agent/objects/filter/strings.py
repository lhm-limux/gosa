# -*- coding: utf-8 -*-
import re
import datetime
from time import mktime
from gosa.agent.objects.filter import ElementFilter, ElementFilterException
import datetime


class ConcatString(ElementFilter):
    """
    Concatenate a string to the current value.

    =========== ===========================
    Key         Description
    =========== ===========================
    appstr      The string to concatenate
    position    The position 'left' or 'right' we want to concatenate the string
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>ConcatString</Name>
    >>>   <Param>Hello Mr. </Param>
    >>>   <Param>left</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...
    """
    def __init__(self, obj):
        super(ConcatString, self).__init__(obj)

    def process(self, obj, key, valDict, appstr, position):
        if type(valDict[key]['value'] != None):
            if position == "right":
                new_val = map(lambda x: x + appstr, valDict[key]['value'] )
            else:
                new_val = map(lambda x: appstr + x, valDict[key]['value'] )
            valDict[key]['value'] = new_val
        return key, valDict


class Replace(ElementFilter):
    """
    Perform a replacement using a reqular expression.

    =========== ===========================
    Key         Description
    =========== ===========================
    regex       The regular expression to use
    replacement The replacement string
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>Replace</Name>
    >>>   <Param>^{([^}]*)}.*$</Param>
    >>>   <Param>Result: \1</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...

    """
    def __init__(self, obj):
        super(Replace, self).__init__(obj)

    def process(self, obj, key, valDict, regex, replacement):
        if type(valDict[key]['value'] != None):
            valDict[key]['value'] = map(lambda x: re.sub(regex, str(replacement), x), valDict[key]['value'])
        return key, valDict


class DateToString(ElementFilter):
    """
    Converts a datetime object into a string.

    =========== ===========================
    Key         Description
    =========== ===========================
    fmt         The outgoing format string. E.g. '%Y%m%d%H%M%SZ'
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>DateToString</Name>
    >>>   <Param>%Y-%m-%d</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...

    """
    def __init__(self, obj):
        super(DateToString, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        if type(valDict[key]['value'] != None):
            valDict[key]['value'] = map(lambda x: x.strftime(fmt), valDict[key]['value'])
        return key, valDict


class TimeToString(DateToString):
    """
    Converts a datetime object into a string.

    =========== ===========================
    Key         Description
    =========== ===========================
    fmt         The outgoing format string. E.g. '%Y%m%d%H%M%SZ'
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>DateToString</Name>
    >>>   <Param>%Y-%m-%d</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...
    """
    def __init__(self, obj):
        super(TimeToString, self).__init__(obj)


class StringToDate(ElementFilter):
    """
    Converts a string object into a datetime.date object..

    =========== ===========================
    Key         Description
    =========== ===========================
    fmt         The format string. E.g. '%Y%m%d%H%M%SZ'
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>StringToDate</Name>
    >>>   <Param>%Y-%m-%d</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...
    """

    def __init__(self, obj):
        super(StringToDate, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        if type(valDict[key]['value'] != None):
            valDict[key]['value'] = map(lambda x: datetime.datetime.strptime(x, fmt).date(), valDict[key]['value'])
        return key, valDict


class StringToTime(ElementFilter):
    """
    Converts a string object into a datetime.datetime object..

    =========== ===========================
    Key         Description
    =========== ===========================
    fmt         The format string. E.g. '%Y%m%d%H%M%SZ'
    =========== ===========================

    e.g.:
    >>> <FilterEntry>
    >>>  <Filter>
    >>>   <Name>StringToTime</Name>
    >>>   <Param>%Y%m%d%H%M%SZ</Param>
    >>>  </Filter>
    >>> </FilterEntry>
    >>>  ...
    """

    def __init__(self, obj):
        super(StringToTime, self).__init__(obj)

    def process(self, obj, key, valDict, fmt="%Y%m%d%H%M%SZ"):
        if type(valDict[key]['value'] != None):
            valDict[key]['value'] = map(lambda x: datetime.datetime.strptime(x, fmt), valDict[key]['value'])
        return key, valDict
