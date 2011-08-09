# -*- coding: utf-8 -*-
import ldap
import pytz
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler
from system_locale import locale_map
from keyboard_models import KeyboardModels

from methods.preseed import PreseedInstallMethod


class BaseInstall(object):

    recipeRecursionDepth = 3

    def __init__(self):
        self.keyboardModels = KeyboardModels().get_models()

    #---> Kickstart stuff
    #  installTemplateDN -> Template Objekt definieren
    #  installNTPServer
    #  installRootEnabled
    #  installRootPasswordHash
    #  installKeyboardlayout  -> Liste
    #  installSystemLocale    -> Liste
    #  installTimezone        -> Liste
    #  installTimeUTC
    #  installRelease         -> Liste
    #  installMirrorDN -> DN des Mirror Systems
    #  installMirrorPoolDN -> DN einer Mirror-Pool-Definition
    #  installKernelPackage   -> Liste
    #  installPartitionTable
    #  installRecipeDN -> Cascadiertes Rezept

    def installGetSystemLocales(self):
        return locale_map

    def installGetKeyboardModels(self):
        return self.keyboardModels

    def installGetKernelPackages(self):
        #TODO: read from repo
        return []

    def installGetTimezones(self):
        return pytz.all_timezones

    def systemGetTemplate(self, mac):
        """ Evaulate template for system with name 'name' """
        data = self.__load_system(mac)
        method = self.systemGetBaseInstallMethod(mac, data)

        # Use the method described by "method" and pass evaluated data
        #TODO: modularize
        print "Method ->", method
        pr = PreseedInstallMethod(data)
        return pr.getBootConfiguration()

    def systemGetBaseInstallMethod(self, mac, data=None):
        # Load system
        if not data:
            data = self.__load_system(mac)

        if not "installTemplateDN" in data:
            raise Exception("system with hardware address '%s' has no install template assigned" % mac)

        # Inspect template for install method
        if not "installMethod" in data:
            return None

        return data["installMethod"]

    def __load_system(self, mac):
        result = {}

        # Load chained entries
        res_queue = []
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=installRecipe)(objectClass=device)(macAddress=%s))" % mac,
                ["installTemplateDN", "installNTPServer", "installRootEnabled",
                 "installRootPasswordHash", "installKeyboardlayout", "installSystemLocale",
                 "installTimezone", "installMirrorDN", "installTimeUTC",
                 "installMirrorPoolDN", "installKernelPackage", "installPartitionTable",
                 "installRecipeDN", "installRelease", "deviceStatus"])

            # Unique?
            if not res:
                raise ValueError("hardware address '%s' cannot be found" % mac)
            if len(res) != 1:
                raise ValueError("hardware address '%s' is not unique" % mac)

            # Add initial object
            dn, obj = res[0]
            print "adding object '%s' to result queue" % dn
            res_queue.append(obj)

            # Trace recipes of present
            depth = self.recipeRecursionDepth
            while 'installRecipeDN' in obj:
                dn = obj['installRecipeDN'][0]
                res = conn.search_s(dn, ldap.SCOPE_BASE, attrlist=[
                    "installTemplateDN", "installNTPServer", "installRootEnabled",
                    "installRootPasswordHash", "installKeyboardlayout", "installSystemLocale",
                    "installTimezone", "installMirrorDN", "installTimeUTC",
                    "installMirrorPoolDN", "installKernelPackage", "installPartitionTable",
                    "installRecipeDN", "installRelease"])
                print "+ adding recipe '%s' to result queue" % dn
                obj = res[0][1]
                res_queue.append(obj)

            # Reverse merge queue into result
            res_queue.reverse()
            for res in res_queue:
                result.update(res)

            # Add template information
            if "installTemplateDN" in result:
                dn = result["installTemplateDN"][0]
                res = conn.search_s(dn, ldap.SCOPE_BASE, attrlist=["installMethod", "templateData"])
                print "+ adding template information"
                if "installMethod" in res[0][1]:
                    result["installMethod"] = res[0][1]["installMethod"][0]
                if "templateData" in res[0][1]:
                    result["templateData"] = res[0][1]["templateData"][0]

        return result

    def systemGetInstallMethod(self, name):
        #-> find with analyzing the objectclasses -> i.e. "puppet", "fai", "opsi"
        raise Exception("Not implemented")

    def systemGetBootParams(self, name):
        #-> depends on system state and base install method
        #-> depending on the system status, add the encrypted key
        raise Exception("Not implemented")

    #TODO: Preseed has to register http service providing the
    #      per preseed config on url


#--- Fun is somewhere else...

Environment.config = "gosa.conf"
Environment.noargs = True
env = Environment.getInstance()
k = BaseInstall()
print k.systemGetTemplate("00:11:22:33:44:88")
