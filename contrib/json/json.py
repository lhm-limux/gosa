# -*- coding: utf-8 -*-
import traceback
import sys
import string
from random import Random
from webob import Request, Response
from webob import exc
from inspect import getargspec
from jsonrpc.json import loads, dumps


def Export(**d_kwargs):
    def decorate(f):
        setattr(f, 'exported', True)
        for k in d_kwargs:
            setattr(f, k, d_kwargs[k])
        return f

    return decorate


def NamedArgs(d_collector):
    def decorate(f):
        d_kwds = {}
        d_args = getargspec(f).args
        d_index = d_args.index(d_collector)

        def new_f(*args, **kwargs):
            # Transfer
            if len(args) > d_index:
                for d_arg in [d for d in d_args if not d in kwargs and d in args[d_index]]:
                    kwargs.update({d_arg: args[d_index][d_arg]})

            f_result = f(*args, **kwargs)

            return f_result

        new_f.__doc__ = f.__doc__
        return new_f

    return decorate


class ObjectFactory(object):
    def __init__(self, proxy, ref, oid, methods, properties, data):
        object.__setattr__(self, "proxy", proxy)
        object.__setattr__(self, "ref", ref)
        object.__setattr__(self, "oid", oid)
        object.__setattr__(self, "methods", methods)
        object.__setattr__(self, "properties", properties)

        for prop in properties:
            object.__setattr__(self, "_" + prop, None if not prop in data else data[prop])

    def _call(self, name, *args):
        ref = object.__getattribute__(self, "ref")
        return object.__getattribute__(self, "proxy").dispatchObjectMethod(ref, name, *args)

    def __getattribute__(self, name):
        if name in object.__getattribute__(self, "methods"):
            return lambda *f: object.__getattribute__(self, "_call")(*[name] + list(f))

        if not name in object.__getattribute__(self, "properties"):
            raise AttributeError("'%s' object has no attribute '%s'" %
                (type(self).__name__, name))

        return object.__getattribute__(self, "_" + name)

    def __setattr__(self, name, value):
        if not name in object.__getattribute__(self, "properties"):
            raise AttributeError("'%s' object has no attribute '%s'" %
                (type(self).__name__, name))

        ref = object.__getattribute__(self, "ref")
        object.__getattribute__(self, "proxy").setObjectProperty(ref, name, value)
        object.__setattr__(self, "_" + name, value)

    def __repr__(self):
        return object.__getattribute__(self, "ref")

    @staticmethod
    def get_instance(proxy, obj_type, ref, oid, methods, properties, data=None):
        return type(obj_type,
                (ObjectFactory, object),
                ObjectFactory.__dict__.copy())(proxy, ref, oid, methods, properties, data)


class JsonRpcApp(object):
    """
    Serve the given object via json-rpc (http://json-rpc.org/)
    """

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(environ, req)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def process(self, environ, req):
        if not req.method == 'POST':
            raise exc.HTTPMethodNotAllowed(
                "Only POST allowed",
                allowed='POST').exception
        try:
            json = loads(req.body)
        except ValueError, e:
            raise ValueError('Bad JSON: %s' % e)
        try:
            method = json['method']
            params = json['params']
            id = json['id']
        except KeyError, e:
            raise ValueError(
                "JSON body missing parameter: %s" % e)
        if method.startswith('_'):
            raise exc.HTTPForbidden(
                "Bad method name %s: must not start with _" % method).exception
        if not isinstance(params, list):
            raise ValueError(
                "Bad params %r: must be a list" % params)
        try:
            method = getattr(self.obj, method)
        except AttributeError:
            raise ValueError(
                "No such method %s" % method)

        # Check permission
        if not hasattr(method, "exported"):
            raise exc.HTTPForbidden(
                "Access to method '%s' is not permitted." % json['method']).exception

        # Add user parameter if needed
        if hasattr(method, "pass_user"):
            params.insert(0, environ['REMOTE_USER'])

        try:
            result = method(*params)
        except:
            text = traceback.format_exc()
            print text
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=text)
            return Response(
                status=500,
                content_type='application/json',
                charset='utf-8',
                body=dumps(dict(result=None, error=error_value, id=id)))
        return Response(
            content_type='application/json',
            charset='utf-8',
            body=dumps(dict(result=result, error=None, id=id)))
