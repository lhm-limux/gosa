# -*- coding: utf-8 -*-

# Import a json library
cjson = None
json = None
try:
    import cjson
except ImportError:
    import json


# Wrap loads/dumps to work with both, cjson and json

def dumps(obj, encoding='utf-8'):
    global cjson
    if cjson:
        return cjson.encode(obj)
    else:
        return json.dumps(obj, encoding=encoding)


def loads(json_string):
    global cjson
    if cjson:
        return cjson.decode(json_string)
    else:
        return json.loads(json_string)


class ServiceException(Exception):
    pass


class ServiceRequestNotTranslatable(ServiceException):
    pass


class BadServiceRequest(ServiceException):
    pass
