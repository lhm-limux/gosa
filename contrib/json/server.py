#!/usr/bin/env python
# -*- coding: utf-8 -*-
import objects
from uuid import uuid1
from types import MethodType
from json import JsonRpcApp, Export
from paste import httpserver
import preseed


class Service(object):
    store = {}

    @Export()
    def closeObject(self, ref):
        if not ref in self.store:
            raise ValueError("reference %s not found" % ref)

        del self.store[ref]

    @Export()
    def setObjectProperty(self, ref, name, value):
        if not ref in self.store:
            raise ValueError("reference %s not found" % ref)
        if not name in self.store[ref]['properties']:
            raise ValueError("property %s not found" % name)

        return setattr(self.store[ref]['object'], name, value)

    @Export()
    def getObjectProperty(self, ref, name):
        if not ref in self.store:
            raise ValueError("reference %s not found" % ref)
        if not name in self.store[ref]['properties']:
            raise ValueError("property %s not found" % name)
        return getattr(self.store[ref]['object'], name)

    @Export()
    def dispatchObjectMethod(self, ref, method, *args):
        if not ref in self.store:
            raise ValueError("reference %s not found" % ref)
        if not method in self.store[ref]['methods']:
            raise ValueError("method %s not found" % name)
        return getattr(self.store[ref]['object'], method)(*args)

    @Export()
    def openObject(self, oid, read_only=False):

        # Use oid to find the object type
        obj_type = self.__get_object_type(oid)
        methods, properties = self.__inspect(obj_type)

        # Load instance, fill with dummy stuff
        ref = str(uuid1())
        obj = obj_type()

        # Store object
        self.store[ref] = {'object': obj, 'methods': methods, 'properties': properties}

        # Build property dict
        propvals = {}
        if properties:
            propvals = dict(map(lambda p: (p, getattr(obj, p)), properties))

        # Build result
        result = {"__jsonclass__":["json.ObjectFactory", [obj_type.__name__, ref, oid, methods, properties]]}
        result.update(propvals)

        return result

    def __get_object_type(self, oid):
        # Hard coded for now...
        obj_type = "preseed.DebianDiskDefinition"
        (module, clazz) = obj_type.rsplit(".", 1)
        return getattr(globals()[module], clazz)

    def __inspect(self, clazz):
        methods = []
        properties = []

        for part in dir(clazz):
            if part.startswith("_"):
                continue
            obj = getattr(clazz, part)
            if isinstance(obj, MethodType):
                methods.append(part)
            if isinstance(obj, property):
                properties.append(part)

        return methods, properties


def main():
    host = "amqp.intranet.gonicus.de"
    port = 8088

    s = Service()

    # Start web service
    app = JsonRpcApp(Service())
    srv = httpserver.serve(app, host, port, start_loop=True)

if __name__ == '__main__':
    main()
