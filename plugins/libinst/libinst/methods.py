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
from gosa.common.env import Environment
from libinst.repository import ConfigItem


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
        if parent:
            self.env.log.info("creating release '%s' with parent '%s'" % (name,
                parent))
        else:
            self.env.log.info("creating release '%s'" % name)

        # Add root node
        release = self._manager._getRelease(name)
        # pylint: disable-msg=E1101
        release.config_items.append(ConfigItem(name="/", item_type=self._root))

        # Try to commit the changes
        try:
            self._manager._session.commit()
        except:
            self._manager._session.rollback()
            raise

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
        return self._supportedItems

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

        if not children:
            children = self._manager._getRelease(release).config_items
            first = True

        def filter_items(item):
            path_match = True
            if path:
                path_match = item.name.startswith(path + "/")

            if item_type:
                return path_match and (item_type == item.item_type)

            return path_match

        items = filter(filter_items, children)
        res = dict((i.getPath(), i.item_type) for i in items)

        # Iterate for items with children
        for item in filter(lambda i: i.children, items):
            res.update(self.listItems(release, item_type, path, item.children))

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

        # Check if this item type is supported
        if not item_type in self._supportedItems:
            raise ValueError("unknown item type '%s'" % item_type)

        # Acquire name from path
        name = os.path.basename(path)

        # Load parent object
        parent = self._get_parent(release, path)

        # Load instance of ConfigItem
        item = self._manager._getConfigItem(name=name, item_type=item_type, add=True)

        # Check if the current path is a container for that kind of
        # item type
        if not item_type in self._supportedItems[parent.item_type]['container']:
            raise ValueError("'%s' is not allowed for container '%s'" %
                    (item_type, parent.item_type))

        # Check if item will be renamed
        if "name" in data and name != data["name"]:
            item.name = data["name"]

        # Add us as child
        parent.children.append(item)

        # Try to commit the changes
        try:
            self._manager._session.commit()
        except:
            self._manager._session.rollback()
            raise

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
        if not children:
            children = self._manager._getRelease(release).config_items

        def filter_path(item):
            return item.name.startswith(path + "/")

        # Remove children if exist
        matches = filter(filter_path, children)
        if matches:
            for child in matches:
                print "Remove", child
                self.removeItem(release, path, child.children)
                self._manager._session.delete(child)

        # Try to commit the changes
        try:
            self._manager._session.commit()
        except:
            self._manager._session.rollback()
            raise

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
        if not children:
            children = self._manager._getRelease(release).config_items

        sub_path = '/'.join(path.split("/")[0:path_level]) or "/"
        matches = filter(lambda p: p.getPath() == sub_path, children)

        if len(matches):
            if path == sub_path:
                return matches[0]
            else:
                return self._get_item(release, path, matches[0].children,
                        path_level=path_level + 1)
        return None

    def _get_parent(self, release, path):
        """
        Internal function to get the parent item for the given path.
        """
        parent = path.rsplit("/", 1)[0] or "/"

        return self._get_item(release, parent)
