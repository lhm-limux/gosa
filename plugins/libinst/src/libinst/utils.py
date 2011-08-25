# -*- coding: utf-8 -*-
import ldap
from gosa.agent.ldap_utils import LDAPHandler


def load_system(device_uuid, mac=None, inherit=True):
    """
    Disable device configuration managmenet.

    =========== ===========================================
    Parameter   Description
    =========== ===========================================
    device_uuid Optional device ID if MAC is not known
    mac         Optional MAC, if device_uuid is not known
    inherit     Enable information inherit mechanism
    =========== ===========================================

    ``Return:`` True on success
    """
    result = {}

    # Potentially fix mac
    if mac:
        mac = mac.replace("-", ":")

    # Load chained entries
    res_queue = []
    lh = LDAPHandler.get_instance()
    with lh.get_handle() as conn:
        fltr = "macAddress=%s" % mac if mac else "deviceUUID=%s" % device_uuid
        res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
            "(&(objectClass=registeredDevice)(%s))" % fltr,
            ["installTemplateDN", "installNTPServer", "installRootEnabled", "macAddress",
             "installRootPasswordHash", "installKeyboardlayout", "installSystemLocale",
             "installTimezone", "installMirrorDN", "installTimeUTC", "installArchitecture",
             "installMirrorPoolDN", "installKernelPackage", "installPartitionTable",
             "installRecipeDN", "installRelease", "deviceStatus", "deviceKey",
             "configMethod", "configItem", "configVariable", "cn", "deviceUUID",
             "objectClass"])

        # Nothing here...
        if not res:
            raise ValueError("device UUID '%s' does not exist" % device_uuid)

        # Unique?
        if len(res) != 1:
            raise ValueError("device UUID '%s' is not unique!?" % device_uuid)

        # Add initial object
        obj_dn, obj = res[0]
        res_queue.append(obj)

        # Skip if we're not using inheritance
        if inherit:
            # Trace recipes of present
            depth = 3
            while 'installRecipeDN' in obj and depth > 0:
                dn = obj['installRecipeDN'][0]
                res = conn.search_s(dn, ldap.SCOPE_BASE, attrlist=[
                    "installTemplateDN", "installNTPServer", "installRootEnabled",
                    "installRootPasswordHash", "installKeyboardlayout", "installSystemLocale",
                    "installTimezone", "installMirrorDN", "installTimeUTC",
                    "installMirrorPoolDN", "installKernelPackage", "installPartitionTable",
                    "installRecipeDN", "installRelease"])
                obj = res[0][1]
                res_queue.append(obj)
                depth += 1

        # Reverse merge queue into result
        res_queue.reverse()
        for res in res_queue:
            result.update(res)

        # Add template information
        if "installTemplateDN" in result:
            dn = result["installTemplateDN"][0]
            res = conn.search_s(dn, ldap.SCOPE_BASE, attrlist=["installMethod", "templateData"])
            if "installMethod" in res[0][1]:
                result["installMethod"] = res[0][1]["installMethod"][0]
            if "templateData" in res[0][1]:
                result["templateData"] = unicode(res[0][1]["templateData"][0], 'utf-8')

        # Add DN information
        result['dn'] = obj_dn

    return result
