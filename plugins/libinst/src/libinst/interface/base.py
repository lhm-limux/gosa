# -*- coding: utf-8 -*-
import ldap
from inspect import stack
from gosa.common import Environment
from gosa.agent.ldap_utils import LDAPHandler, unicode2utf8, normalize_ldap
from libinst.utils import load_system


class BaseInstallMethod(object):
    """
    This is the base install method interface class. It defines all relevant methods
    needed to interact with any install method. Implementations of this interface
    must implement all methods.
    """
    attributes = {
            'installNTPServer': 'ntp-servers',
            'installRootEnabled': 'root-user',
            'installRootPasswordHash': 'root-hash',
            'installKeyboardLayout': 'keyboard-layout',
            'installSystemLocale': 'system-locale',
            'installTimezone': 'timezone',
            'installTimeUTC': 'utc',
            'installRelease': 'release',
            'installPartitionTable': 'disk-setup',
            'installKernelPackage': 'kernel',
        }

    def __init__(self):
        self.rev_attributes = dict((v,k) for k, v in self.attributes.iteritems())
        self.env = Environment.getInstance()

    @staticmethod
    def getInfo():
        """
        Static method to get information for the current install method implementation.

        The result is a dictionary with the following keys:

        ============== ========================================
        Key            Description
        ============== ========================================
        name            Display name of the method
        title           Short description of the method
        description     Description of the method
        repositories    List of supported repository types
        methods         List of supported configuration methods
        ============== ========================================

        ``Return:`` dict
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def addClient(self, device_uuid):
        """
        Add a client to the base install implementation.

        =============== =================
        Parameter       Description
        =============== =================
        device_uuid     Unique device ID
        =============== =================

        ``Return:`` True on success
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def removeClient(self, device_uuid):
        """
        Remove a client from the base install implementation.

        =============== =================
        Parameter       Description
        =============== =================
        device_uuid     Unique device ID
        =============== =================

        ``Return:`` True on success
        """
        raise NotImplementedError("%s is not implemented" % stack()[0][3])

    def getBootString(self, device_uuid, mac=None):
        """
        Generate the boot string for that system when running from PXE.

        =============== =================
        Parameter       Description
        =============== =================
        device_uuid     Optional device_uuid
        mac             Optional MAC
        =============== =================

        ``Return:`` string
        """
        return ""

    def getBootParams(self, device_uuid, mac=None):
        """
        Return boot parameters needed for that install method.

        =============== ====================
        Parameter       Description
        =============== ====================
        device_uuid     Optional device_uuid
        mac             Optional MAC
        =============== ====================

        ``Return:`` list
        """
        return []

    def getBootConfiguration(self, device_uuid, mac=None):
        """
        Return the complete boot configuration file (template) needed to do a base
        bootstrapping.

        =============== ====================
        Parameter       Description
        =============== ====================
        device_uuid     Optional device_uuid
        mac             Optional MAC
        =============== ====================

        ``Return:`` string
        """
        return None

    def getBaseInstallParameters(self, device_uuid, data=None):
        """
        Return parameters used to bootstrap a device.

        =============== ====================
        Parameter       Description
        =============== ====================
        device_uuid     Unique device ID
        =============== ====================

        Please take a look at
        :meth:`libinst.interface.BaseInstallMethod.setBaseInstallParameters`
        for more information about the returned properties.

        ``Return:`` dict
        """
        res = {}
        if not data:
            data = load_system(device_uuid, None, False)

        for key, value in self.attributes.items():
            if key in data:
                res[value] = data[key]

        if 'installTemplateDN' in data:
            lh = LDAPHandler.get_instance()
            with lh.get_handle() as conn:
                lres = conn.search_s(data['installTemplateDN'][0],
                        ldap.SCOPE_BASE, "(objectClass=installTemplate)", ["cn"])

            res['template'] = lres[0][1]['cn'][0]

        return res

    def setBaseInstallParameters(self, device_uuid, data, current_data=None):
        """
        Set the system base install parameters that are used
        to fill up the template.

        =============== ==============================
        Parameter       Description
        =============== ==============================
        device_uuid     Unique device ID
        data            Hash describing the parameters
        =============== ==============================

        The return parameters are encoded as a dictionary with these keys:

        =============== ======================================================
        Key             Description
        =============== ======================================================
        utc             Flag to specify if system uses UTC
        timezone        String to specify time zone
        ntp-servers     List of time server names/IPs
        kernel          The boot kernel package name
        root-hash       Hashed version of the root password
        root-user       Flag to decide if there's a root user
        disk-setup      String oriented at the RedHat kickstart device string
        template        String containing the system template
        system-locale   Locale definition for the system
        release         Release to install on the system
        keyboard-layout Keyboard layout to use
        =============== ======================================================

        ``Return:`` dict
        """
        # Load device
        if not current_data:
            current_data = load_system(device_uuid, None, False)

        is_new = not 'installRecipe' in current_data['objectClass']
        dn = current_data['dn']
        current_data = self.getBaseInstallParameters(device_uuid, current_data)

        mods = []

        # Add eventually missing objectclass
        if is_new:
            mods.append((ldap.MOD_ADD, 'objectClass', 'installRecipe'))

        # Transfer changed parameters
        for ldap_key, key in self.attributes.items():

            # New value?
            if key in data and not key in current_data:
                mods.append((ldap.MOD_ADD, ldap_key,
                    normalize_ldap(unicode2utf8(data[key]))))
                continue

            # Changed value?
            if key in data and key in current_data \
                    and data[key] != current_data[key]:

                mods.append((ldap.MOD_REPLACE, ldap_key,
                    normalize_ldap(unicode2utf8(data[key]))))
                continue

        # Removed values
        for key in current_data.keys():
            if key in self.rev_attributes and not key in data:
                mods.append((ldap.MOD_DELETE, self.rev_attributes[key], None))

        # Do LDAP operations to add the system
        res = None
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            res = conn.search_s(",".join([self.env.config.get("libinst.template-rdn",
                "cn=templates,cn=libinst,cn=config"), lh.get_base()]),
                ldap.SCOPE_SUBTREE, "(&(objectClass=installTemplate)(cn=%s))" % data['template'], ["cn"])
            if len(res) != 1:
                raise ValueError("template '%s' not found" % data['template'])

            template_dn = res[0][0]
            if is_new:
                mods.append((ldap.MOD_ADD, 'installTemplateDN', [template_dn]))
            else:
                mods.append((ldap.MOD_REPLACE, 'installTemplateDN', [template_dn]))

            res = conn.modify_s(dn, mods)

        return res

    def removeBaseInstallParameters(self, device_uuid, data=None):
        """
        Disable device base install capabilities.

        =========== ===========================================
        Parameter   Description
        =========== ===========================================
        device_uuid Unique identifier of a device
        =========== ===========================================
        """
        if not data:
            data = load_system(device_uuid)

        mods = [(ldap.MOD_DELETE, 'objectClass', 'installRecipe')]
        for attr in self.attributes.keys() + ["installTemplateDN"]:
            if attr in data:
                mods.append((ldap.MOD_DELETE, attr, None))

        # Do LDAP operations to remove the device
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            conn.modify_s(data['dn'], mods)

    #TODO: getter and setter for that...
    #  installMirrorDN        -> DN des Mirror Systems
    #  installMirrorPoolDN    -> DN einer Mirror-Pool-Definition
    #  installTemplateDN      -> DN eines Templates
    #  installRecipeDN        -> Cascadiertes Rezept
    #--------------------------------------------------------------------------
