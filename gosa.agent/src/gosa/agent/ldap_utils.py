# -*- coding: utf-8 -*-
"""
This code is part of GOsa (http://www.gosa-project.org)
Copyright (C) 2009, 2010 GONICUS GmbH

ID: $$Id: ldap_utils.py 997 2010-09-28 15:09:46Z cajus $$

See LICENSE for more information about the licensing.
"""
import ldapurl
import ldap.sasl
import types
from contextlib import contextmanager
from gosa.common.env import Environment


class LDAPHandler(object):

    connection_handle = []
    connection_usage  = []
    instance = None

    def __init__(self):
        self.env = Environment.getInstance()

        # Initialize from configuration
        getOption = self.env.config.get
        self.__url = ldapurl.LDAPUrl(get("ldap.url"))
        self.__bind_user = get('ldap.bind_user', default=None)
        self.__bind_dn = get('ldap.bind_dn', default=None)
        self.__bind_secret = get('ldap.bind_secret', default=None)
        self.__pool = int(get('ldap.pool_size', default=10))

        # Sanity check
        if self.__bind_user and not ldap.SASL_AVAIL:
            raise Exception("bind_user needs SASL support, which doesn't seem to be available in python-ldap")

        # Initialize static pool
        LDAPHandler.connection_handle = [None] * self.__pool
        LDAPHandler.connection_usage = [False] * self.__pool

    def get_base(self):
        return self.__url.dn

    def get_connection(self):
        # Are there free connections in the pool?
        try:
            next_free = LDAPHandler.connection_usage.index(False)
        except ValueError:
            raise Exception("no free LDAP connection available")

        # Need to initialize?
        if not LDAPHandler.connection_handle[next_free]:
            getOption = self.env.config.get
            self.env.log.debug("initializing LDAP connection to %s" %
                    str(self.__url))
            conn = ldap.ldapobject.ReconnectLDAPObject("%s://%s" % (self.__url.urlscheme,
                self.__url.hostport),
                retry_max=int(get("ldap.retry_max", default=3)),
                retry_delay=int(get("ldap.retry_delay", default=5)))

            # If no SSL scheme used, try TLS
            if ldap.TLS_AVAIL and self.__url.urlscheme != "ldaps":
                try:
                    conn.start_tls_s()
                except ldap.PROTOCOL_ERROR as detail:
                    self.env.log.debug("cannot use TLS, falling back to unencrypted session")

            try:
                # Simple bind?
                if self.__bind_dn:
                    self.env.log.debug("starting simple bind using '%s'" %
                        self.__bind_dn)
                    conn.simple_bind_s(self.__bind_dn, self.__bind_secret)
                else:
                    self.env.log.debug("starting SASL bind using '%s'" %
                        self.__bind_user)
                    auth_tokens = ldap.sasl.digest_md5(self.__bind_user, self.__bind_secret)
                    conn.sasl_interactive_bind_s("", auth_tokens)

            except ldap.INVALID_CREDENTIALS as detail:
                self.env.log.error("LDAP authentication failed: %s" %
                        str(detail))

            LDAPHandler.connection_handle[next_free] = conn

        # Lock entry
        LDAPHandler.connection_usage[next_free] = True

        return LDAPHandler.connection_handle[next_free]

    def free_connection(self, conn):
        index = LDAPHandler.connection_handle.index(conn)
        LDAPHandler.connection_usage[index] = False

    @contextmanager
    def get_handle(self):
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.free_connection(conn)

    @staticmethod
    def get_instance():
        if not LDAPHandler.instance:
            LDAPHandler.instance = LDAPHandler()
        return LDAPHandler.instance

def map_ldap_value(value):
    if type(value) == types.BooleanType:
        return "TRUE" if value else "FALSE"
    if type(value) == types.UnicodeType:
        return value.encode('utf-8')
    if type(value) == types.ListType:
        return map(lambda x: map_ldap_value(x), value)
    return value

def unicode2utf8(data):
    return map_ldap_value(data)

def normalize_ldap(data):
    if type(data) != types.ListType:
        return [data]

    return data
