# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2011 GONICUS GmbH

 See LICENSE for more information about the licensing.
"""
import re
from urlparse import urlparse
from gosa.common.env import Environment
from gosa.common.components.registry import PluginRegistry
from libinst.methods import load_system
from libinst.methods import BaseInstallMethod
from libinst.disk import DiskDefinition, LINUX, ALL
from webob import exc, Request, Response
from libinst.boot.preseed.disk import DebianDiskDefinition


class DebianPreseed(BaseInstallMethod):

    http_subtree = True

    @staticmethod
    def getInfo():
        return {
            "name": "Preseed",
            "title": "Debian preseed installation method",
            "description": "Base installation using the debian installer",
            "repositories": ["deb"],
            "methods": ["puppet"]}

    def __init__(self):
        super(DebianPreseed, self).__init__()
        self.env = Environment.getInstance()
        self.path = self.env.config.getOption('path', 'libinst', default="/preseed")

        # Get http service instance
        self.__http = PluginRegistry.getInstance('HTTPService')

        # Register ourselves
        self.__http.register(self.path, self)

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(req, environ)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def process(self, req, environment):
        if not req.method == 'GET':
            raise exc.HTTPMethodNotAllowed(
                "Only GET allowed").exception

        try:
            # Try to find a device uuid for the device
            data = self.getBootConfiguration(None,
                 mac=req.path.split("/")[-1].replace("-", ":"))
            res = Response(data, "200 OK", [("Content-type", "text/plain; charset='utf-8'"),])
            return res

        except Exception as e:
            print e
            pass

        e = exc.HTTPNotFound(location=req.path_info)
        return req.get_response(e)

    def __attr_map(self, source, default=None, data=None):
        if not source in data:
            return default

        return data[source][0]

    def __load_release(self, data):
        release_path = data["installRelease"][0]

        #TODO: find configured mirror
        #      by inspecting installMirrorDN / installMirrorPoolDN
        #      for the moment, load it from the configuration file
        #      -> check if release_path debian/squeeze/1.0 is supported
        #         for the mirror
        #      -> if not available, automatically choose a mirror
        url = urlparse(self.env.config.getOption(
            'http_base_url', section='repository'))

        return {
            'mirror_protocol': url.scheme,
            'mirror_host': url.netloc,
            'mirror_path': url.path,
            'suite': "/".join(release_path.split("/")[1:]),
            }

    def __console_layout_code(self, data):
        return self.__attr_map("installSystemLocale", "en_US.UTF-8", data=data).split(".")[0]

    def __ntp(self, data):
        if not "installNTPServer" in data:
            return "d-i clock-setup/ntp boolean false"

        # Return space separated list of servers
        return "d-i clock-setup/ntp boolean true\n" + \
            "d-i clock-setup/ntp-server string " + \
            " ".join(data["installNTPServer"])

    def __kernel_package(self, data):
        if not "installKernelPackage" in data:
            return ""

        # Fill the kernel package
        return "d-i base-installer/kernel/image string " + data["installKernelPackage"][0]

    def __partition(self, data):
        if not "installPartitionTable" in data:
            return ""

        # Instanciate disk definition
        dd = DebianDiskDefinition(data['installPartitionTable'][0])
        return str(dd)

    def getBootConfiguration(self, device_uuid, mac=None):
        super(DebianPreseed, self).getBootConfiguration(device_uuid, mac)

        # Load device data
        data = load_system(device_uuid, mac)

        # Attribute conversion
        mapped_data = {
            'installer_locale': self.__attr_map("installSystemLocale", "en_US.UTF-8", data=data),
            'installer_keymap': self.__attr_map("installKeyboardLayout", "us", data=data),
            'console_keymap': self.__attr_map("installKeyboardLayout", "us", data=data),
            'console_layout_code': self.__console_layout_code(data=data),
            'time_utc': "true" if self.__attr_map("installTimeUTC", "TRUE", data=data) == "TRUE" else "false",
            'time_zone': self.__attr_map("installTimezone", "GMT", data=data),
            'ntp': self.__ntp(data=data),
            'root_login_enabled': "true" if self.__attr_map("installRootEnabled", "FALSE", data=data) == "TRUE" else "false",
            'root_password_md5': self.__attr_map("installRootPasswordHash", "$1$2wd8zNj7$eWsmsB/lVdY/m4T8wi65W1", data=data),
            'kernel_package': self.__kernel_package(data=data),
            'partition': self.__partition(data=data),
            }
        mapped_data.update(self.__load_release(data=data))

        return data['templateData'].format(**mapped_data)

    def getBootParams(self, device_uuid, mac=None):
        super(DebianPreseed, self).getBootParams(device_uuid, mac)

        # Load device data
        data = load_system(device_uuid, mac)

        arch = data["installArchitecture"][0]
        keymap = data["installKeyboardLayout"][0] \
            if "installKeyboardLayout" in data else "us"
        locale = data["installSystemLocale"][0] \
            if "installSystemLocale" in data else "en_US.UTF-8"

        url = "%s://%s:%s/%s/%s" % (
            self.__http.scheme,
            self.__http.host,
            self.__http.port,
            self.path.lstrip("/"),
            data['macAddress'][0].replace(":", "-"))

        hostname = data['cn'][0]
        #TODO: take a look at RFC 1279 before doing anything else
        domain = "please-fixme.org"

        params = [
            "vga=normal",
            "initrd=debian-installer/%s/initrd.gz" % arch,
            "netcfg/choose_interface=eth0",
            "locale=%s" % locale[:5],
            "debian-installer/country=%s" % locale[3:5],
            "debian-installer/language=%s" % locale[0:2],
            "debian-installer/keymap=%s" % keymap,
            "console-keymaps-at/keymap=%s" % keymap,
            "auto-install/enable=false",
            "preseed/url=%s" % url,
            "debian/priority=critical",
            "hostname=%s" % hostname,
            "domain=%s" % domain,
            "DEBCONF_DEBUG=5",
            ]

        return params
