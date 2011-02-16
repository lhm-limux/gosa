# -*- coding: utf-8 -*-
from webob import Request, Response
from webob import exc
from simplejson import loads, dumps
from model import Instance, User, get_session
import traceback
import sys


def Export(**kwds):
    def decorate(f):
        setattr(f, 'exported', True)
        for k in kwds:
            setattr(f, k, kwds[k])
        return f
    return decorate


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

        # If roles != ALL, check for membership
        allow = "ALL"
        if hasattr(method, "allow"):
            allow = getattr(method, "allow")

        if allow != "ALL":
            session = get_session()

            if allow == "REGISTERED_INSTANCE":

                if session.query(Instance).filter(Instance.uuid == environ['REMOTE_USER']).count() != 1:
                    raise exc.HTTPForbidden(
                        "Access to method '%s' is not permitted." % json['method']).exception

            elif  allow == "REGISTERED_USER":

                if session.query(User).filter(User.uid == environ['REMOTE_USER']).count() != 1:
                    raise exc.HTTPForbidden(
                        "Access to method '%s' is not permitted." % json['method']).exception

            else:

                # Check if "allow" is in the users roles
                query = session.query(User).filter(User.uid == environ['REMOTE_USER'])
                user = query.first()
                if not allow in user.roles:
                    raise exc.HTTPForbidden(
                        "Access to method '%s' is not permitted." % json['method']).exception

        # Add user parameter if needed
        if hasattr(method, "pass_user"):
            params.insert(0, environ['REMOTE_USER'])

        try:
            result = method(*params)
        except:
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=text)
            return Response(
                status=500,
                content_type='application/json',
                body=dumps(dict(result=None,
                                error=error_value,
                                id=id)))
        return Response(
            content_type='application/json',
            body=dumps(dict(result=result,
                            error=None,
                            id=id)))
