# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: methods.py 1225 2010-10-21 14:19:54Z janw $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
import re
import os
import ldap
import sys
from types import StringTypes, DictType
from gosa.common.env import Environment
from gosa.agent.ldap_utils import LDAPHandler, unicode2utf8
from libinst.entities.config_item import ConfigItem


class InstallItem(object):

    _changed = False
    _prefix = ""

    def __init__(self, path, name):
        pass

    def set(self, name, values):
        # pylint: disable-msg=E1101
        if not name in self._options:
            raise ValueError("unknown property '%s'" % name)

        # Convert to array
        if type(values).__name__ != "list":
            check_values = [values]
        else:
            check_values = values

        # Regex check value?
        # pylint: disable-msg=E1101
        if "syntax" in self._options[name]:
            for value in check_values:
                # pylint: disable-msg=E1101
                if not re.match(self._options[name]["syntax"], value):
                    raise ValueError("value '%s' provided for '%s' is invalid" % (value, name))
        # pylint: disable-msg=E1101
        if "check" in self._options[name]:
            for value in check_values:
                # pylint: disable-msg=E1101
                if not self._options[name]["check"](value):
                    raise ValueError("value '%s' provided for '%s' is invalid" % (value, name))

        # Updated value if needed
        # pylint: disable-msg=E1101
        if self._options[name]['value'] != values:
            # pylint: disable-msg=E1101
            self._options[name]['value'] = values
            self._changed = True

    def get(self, name):
        # pylint: disable-msg=E1101
        if not name in self._options:
            raise ValueError("unknown property '%s'" % name)

        # pylint: disable-msg=E1101
        return self._options[name]['value']

    def get_options(self):
        return dict((k, v['value']) for k, v in
                # pylint: disable-msg=E1101
                self._options.iteritems())

    def commit(self):
        # Before writing data back, validate myself
        self._validate()

    def _validate(self):
        # pylint: disable-msg=E1101
        for opt, data in self._options.iteritems():
            if data['required'] and not data['value']:
                raise ValueError("item '%s' is mandatory" % opt)

    def scan(self):
        return {}

    def getAssignableElements(self):
        return {}


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
            'installKeyboardlayout': 'keyboard-layout',
            'installSystemLocale': 'system-locale',
            'installTimezone': 'timezone',
            'installTimeUTC': 'utc',
            'installRelease': 'release',
            'installPartitionTable': 'disk-setup',
            'installKernelPackage': 'kernel',
        }

    def __init__(self):
        self.rev_attributes = dict((v,k) for k, v in self.attributes.iteritems())

    @staticmethod
    def getInfo():
        """
        Get information for the current install method implementation.

        @rtype: dict
        @return: A dict containing name, title and description
        """
        return None

    def getBootParams(self, device_uuid, mac=None):
        """
        Return boot parameters needed for that install method.

        @rtype: list
        @return: list of boot parameters
        """
        return []

    def getBootConfiguration(self, device_uuid, mac=None):
        """
        Return the complete boot configuration file needed to do a base
        bootstrapping.

        @rtype: string
        @return: multi line text
        """
        return None

    def getBaseInstallParameters(self, device_uuid, data=None):
        res = {}
        if not data:
            data = load_system(device_uuid, False)

        for key, value in self.attributes.items():
            if key in data:
                res[value] = data[key]
            else:
                res[value] = None

        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            lres = conn.search_s(data['installTemplateDN'][0],
                    ldap.SCOPE_BASE, "(objectClass=installTemplate)", ["cn"])

        res['template'] = lres[0][1]['cn'][0]

        return res

    def setBaseInstallParameters(self, device_uuid, data, current_data=None):
        # Load device
        if not current_data:
            current_data = load_system(device_uuid, False)

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
                    unicode2utf8(data[key])))
                continue

            # Changed value?
            if key in data and key in current_data \
                    and data[key] != current_data[key]:

                mods.append((ldap.MOD_REPLACE, ldap_key,
                    unicode2utf8(data[key])))
                continue

        # Removed values
        for key in current_data.keys():
            if key in self.rev_attributes and not key in data:
                mods.append((ldap.MOD_DELETE, self.rev_attributes[key], None))

        # Do LDAP operations to add the system
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            res = conn.search_s(",".join([self.env.config.getOption("template-rdn",
                "libinst", "cn=templates,cn=libinst,cn=config"), lh.get_base()]),
                ldap.SCOPE_SUBTREE, "(&(objectClass=installTemplate)(cn=%s))" % data['template'], ["cn"])
            if len(res) != 1:
                raise ValueError("template '%s' not found" % data['template'])

            template_dn = res[0][0]
            if is_new:
                mods.append((ldap.MOD_ADD, 'installTemplateDN', [template_dn]))
            else:
                mods.append((ldap.MOD_REPLACE, 'installTemplateDN', [template_dn]))

            print mods

            conn.modify_s(dn, mods)

    def removeBaseInstallParameters(self, device_uuid, data=None):
        if not data:
            data = load_system(device_uuid)

        mods = [(ldap.MOD_DELETE, 'objectClass', 'installRecipe')]
        for attr in self.attributes.keys() + ["installTemplateDN"]:
            mods.append((ldap.MOD_DELETE, attr, None))

        # Do LDAP operations to remove the device
        lh = LDAPHandler.get_instance()
        with lh.get_handle() as conn:
            conn.modify_s(dn, mods)

    #TODO: getter and setter for that...
    #  installMirrorDN        -> DN des Mirror Systems
    #  installMirrorPoolDN    -> DN einer Mirror-Pool-Definition
    #  installTemplateDN      -> DN eines Templates
    #  installRecipeDN        -> Cascadiertes Rezept
    #--------------------------------------------------------------------------


class InstallMethod(object):
    """
    This is the install method interface class. It defines all relevant methods
    needed to interact with any install method. Implementations of this interface
    must implement all methods.
    """

    _supportedTypes = []
    _supportedItems = {}

    def __init__(self, manager):
        self.env = Environment.getInstance()
        self._manager = manager

    @staticmethod
    def getInfo():
        """
        Get information for the current install method implementation.

        @rtype: dict
        @return: A dict containing name, title and description
        """
        return None

    def getSupportedTypes(self):
        """
        Return the list of supported repository types.

        @rtype: list
        @return: List of repository types
        """
        return self._supportedTypes

    def createRelease(self, name, parent=None):
        """
        Makes the specified release available in the config
        management system.

        @type name: string
        @param name: release path

        @type parent: string
        @param parent: path of the optional
            parent release. Data from the parent release gets
            duplicated for the new one.

        @rtype: bool
        @return: True - success
        """
        session = None

        try:
            session = self._manager.getSession()
            if parent:
                parent = session.merge(parent)
                self.env.log.info("creating release '%s' with parent '%s'" % (name, parent))
            else:
                self.env.log.info("creating release '%s'" % name)

            # Add root node
            release = self._manager._getRelease(name)
            release = session.merge(release)
            # pylint: disable-msg=E1101
            release.config_items.append(ConfigItem(name="/", item_type=self._root))

            # Try to commit the changes
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def removeRelease(self, name, recursive=False):
        """
        Removes the specified release available from the config
        management system.

        @type name: string
        @param name: release path

        @type recursive: bool
        @param recursive: Remove child releases, too.

        @rtype: bool
        @return: True - success
        """
        self.env.log.info("Removing release '%s'" % name)

    def renameRelease(self, old_name, new_name):
        """
        Rename a release inside the config management
        system. Subreleases will be renamed, too.

        @type old_name: string
        @param old_name: release path

        @type new_name: string
        @param new_name: release path

        @rtype: bool
        @return: True - success
        """

        # Only allow renaming of the latter part
        if old_name.rsplit("/", 1)[0] != new_name.rsplit("/", 1)[0]:
            raise ValueError("moving of releases is not allowed")

        self.env.log.info("renaming release '%s' to '%s'" % (old_name, new_name))

    def getItemTypes(self):
        """
        Returns a dict of name/description pairs for the
        current backend.

        @rtype: dict
        @return: dict of name/info pairs

            'name' : {
                'description': 'text',
                'container': [item_type,...],
                'interface': "text",
                }

        """
        res = {}

        for item, value in self._supportedItems.items():
            res[item] = {
                    "name": value['name'],
                    "description": value['description'],
                    "container": value['container'],
                    "options": {},
                    }

            # Copy all elements that do not contain objects
            for oitem, ovalue in value['options'].items():
                res[item]['options'][oitem] = {}
                for ditem, dvalue in ovalue.items():
                    if ditem != "check":
                        res[item]['options'][oitem][ditem] = dvalue
        return res

    def listAssignableElements(self, release):
        res = {}
        for item in self._manager._getAssignableElements(release):
            res.append(item.getAssignableElements())
        return res

    def listItems(self, release, item_type=None, path=None, children=None):
        """
        Returns a list of items of item_type (if given) for
        the specified release - or all.

        @type release: string
        @param release: release path

        @type item_type: string
        @param item_type: type of item to list, None for all

        @type path: string
        @param path: path to list items on

        @rtype: dict
        @return: dictionary of name/item_type pairs
        """
        res = {}
        first = False
        session = None

        def filter_items(item):
            path_match = True
            if path:
                path_match = item.name.startswith(path + "/")

            if item_type:
                return path_match and (item_type == item.item_type)

            return path_match

        try:
            session = self._manager.getSession()
            if isinstance(release, StringTypes):
                instance = self._manager._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)

            if not children:
                children = release.config_items
                first = True
            else:
                children = session.merge(children)

            items = filter(filter_items, children)
            res = dict((i.getPath(), i.item_type) for i in items)

            # Iterate for items with children
            for item in filter(lambda i: i.children, items):
                res.update(self.listItems(release, item_type, path, item.children))

            session.commit()

        except:
            session.rollback()
            raise
        finally:
            session.close()

        return res

    def getItem(self, release, path):
        """
        Return the data of specified item.

        @type release: string
        @param release: release path

        @type path: string
        @param path: item path inside of the structure

        @rtype: json-string
        @return: the encoded data of the item, depending on the format
            definition.
        """
        pass

    def setItem(self, release, path, item_type, data):
        """
        Set the data for the specified item.

        @type release: string
        @param release: release path

        @type path: string
        @param path: item path inside of the structure, including
            the name as last element of the path.

        @type item_type: string
        @param item_type: the item type to create

        @type data: json-string
        @param data: the encoded data item

        @rtype: bool
        @return: True = success
        """
        session = None

        # Check if this item type is supported
        if not item_type in self._supportedItems:
            raise ValueError("unknown item type '%s'" % item_type)

        # Acquire name from path
        name = os.path.basename(path)

        try:
            session = self._manager.getSession()

            # Load parent object
            parent = self._get_parent(release, path)
            if not parent:
                raise ValueError("cannot find parent object for '%s'" % path)
            parent = session.merge(parent)

            # Check if the current path is a container for that kind of
            # item type
            if not item_type in self._supportedItems[parent.item_type]['container']:
                raise ValueError("'%s' is not allowed for container '%s'" %
                        (item_type, parent.item_type))

            # Load instance of ConfigItem
            item = self._manager._getConfigItem(name=name, item_type=item_type, release=release, add=True)
            session.commit() # FIXME: Does not work without this commit??
            item = session.merge(item)
            item.path = path

            # Check if item will be renamed
            if "name" in data and name != data["name"]:
                item.name = data["name"]

            # Updated marker for assignable elements
            item.assignable = bool(item.getAssignableElements())

            # Add us as child
            release_object = self._manager._getRelease(release)
            release_object = session.merge(release_object)
            release_object.config_items.append(item)
            parent.children.append(item)

            # Try to commit the changes
            session.commit()
        except:
            self.env.log.error("Caught unknown exception %s" % sys.exc_info()[0])
            session.rollback()
            raise
        finally:
            session.close()

    def removeItem(self, release, path, children=None):
        """
        Remove the specified item and it's children.

        @type release: string
        @param release: release path

        @type path: string
        @param path: item path inside of the structure, including
            the name as last element of the path.

        @rtype: bool
        @return: True = success
        """
        session = None

        def filter_path(item):
            if item.path:
                return item.path.startswith(path + "/")

            return False

        try:
            session = self._manager.getSession()
            if isinstance(release, StringTypes):
                instance = self._manager._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)

            if not children:
                children = release.config_items

            # Remove children if exist
            matches = filter(filter_path, children)
            if matches:
                for child in matches:
                    session.delete(child)

            # Remove self
            for me in children:
                if path == me.path:
                    session.delete(me)
                    break

            # Try to commit the changes
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def scan(self, release):
        """
        Re-scan the specified release and update the database stored
        path information.

        @type release: string
        @param release: release path
        """
        path = "/"
        # pylint: disable-msg=E1101
        containers = self._supportedItems[self._root]['container']

        print "-"*80
        # pylint: disable-msg=E1121
        result = self._scan(path, self.getBaseDir(release), containers)
        print result
        print "-"*80

        # Update DB from Scan
        self._manager._replaceConfigItems(release, result)

    def _scan(self, path, abs_path, containers):
        """
        Internal helper function for 'scan' method.
        """
        res = {}
        for container in containers:
            module = self._supportedItems[container]['module']
            items = module.scan(abs_path)

            for item, item_abs_path in items.iteritems():
                item_path = "/".join([path.rstrip("/"), item])
                res[item_path] = container

                if module._container:
                    res.update(self._scan(item_path, item_abs_path, module._container))

        return res

    def getBaseDir(self):
        """
        Return the methods "working" directory

        @rtype: string
        @return: Working directory
        """
        return None

    def getBootParams(self):
        """
        Return boot parameters needed for that install method.

        @rtype: list
        @return: list of boot parameters
        """
        return []

    def _get_relative_path(self, release, path):
        """
        Internal function to evaluate the relative path for
        an item in the filesystem.

        @type release: string
        @param release: release path

        @type path: string
        @param path: item path inside of the structure, including
            the name as last element of the path.

        @rtype: string
        @return: relative path
        """
        relative_path = ""
        current_path = ""

        # Add the item prefix for every path element after
        # checking for the item type
        for path_element in path.split("/")[1:]:
            current_path += "/" + path_element
            item = self._get_item(release, current_path)

            if not item:
                raise ValueError("path '%s' does not exist", path)

            module = self._supportedItems[item.item_type]['module']
            relative_path += os.path.join(module._prefix, path_element)

        return relative_path

    def _get_item(self, release, path, children=None, path_level=1):
        """
        Internal function to return the item specified by 'path'.

        @type release: string
        @param release: release path

        @type path: string
        @param path: item path inside of the structure, including
            the name as last element of the path.

        @rtype: ConfigItem
        @return: The item specified by 'path'
        """
        result = None
        session = None

        try:
            session = self._manager.getSession()
            if isinstance(release, StringTypes):
                instance = self._manager._getRelease(release)
                if instance is None:
                    raise ValueError("Unknown release %s" % release)
                else:
                    release = instance
            release = session.merge(release)

            if not children:
                children = release.config_items

            sub_path = '/'.join(path.split("/")[0:path_level]) or "/"
            matches = filter(lambda p: p.getPath() == sub_path, children)

            if len(matches):
                if path == sub_path:
                    result = matches[0]
                else:
                    result = self._get_item(release, path, matches[0].children,
                            path_level=path_level + 1)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

        return result

    def _get_parent(self, release, path):
        """
        Internal function to get the parent item for the given path.
        """
        result = None
        session = None
        parent = path.rsplit("/", 1)[0] or "/"
        try:
            session = self._manager.getSession()
            result = self._get_item(release, parent)
            if result:
                result = session.merge(result)
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        return result


def load_system(device_uuid, mac=None, inherit=True):
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
             "cn", "deviceUUID", "objectClass"])

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
            while 'installRecipeDN' in obj:
                dn = obj['installRecipeDN'][0]
                res = conn.search_s(dn, ldap.SCOPE_BASE, attrlist=[
                    "installTemplateDN", "installNTPServer", "installRootEnabled",
                    "installRootPasswordHash", "installKeyboardlayout", "installSystemLocale",
                    "installTimezone", "installMirrorDN", "installTimeUTC",
                    "installMirrorPoolDN", "installKernelPackage", "installPartitionTable",
                    "installRecipeDN", "installRelease"])
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
            if "installMethod" in res[0][1]:
                result["installMethod"] = res[0][1]["installMethod"][0]
            if "templateData" in res[0][1]:
                result["templateData"] = unicode(res[0][1]["templateData"][0], 'utf-8')

        # Add DN information
        result['dn'] = obj_dn


    return result
