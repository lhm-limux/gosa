# -*- coding: utf-8 -*-
import re


class InstallItem(object):
    """
    Create an install item instance, *name* it and place it on
    *path*.

    =========== ======================
    Parameter   Description
    =========== ======================
    path        name
    =========== ======================
    """

    _changed = False
    _prefix = ""

    def __init__(self, path, name):
        pass

    def set(self, name, values):
        """
        Set the property given by *name* to value given by *value*.

        =========== ======================
        Parameter   Description
        =========== ======================
        name        Property name
        value       Property value
        =========== ======================
        """
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
        """
        Get the property given by *name*.

        =========== ======================
        Parameter   Description
        =========== ======================
        name        Property name
        =========== ======================

        ``Return:`` misc
        """
        # pylint: disable-msg=E1101
        if not name in self._options:
            raise ValueError("unknown property '%s'" % name)

        # pylint: disable-msg=E1101
        return self._options[name]['value']

    def get_options(self):
        """
        Get all properties as a key/value pair.

        ``Return:`` dict
        """
        return dict((k, v['value']) for k, v in
                # pylint: disable-msg=E1101
                self._options.iteritems())

    def commit(self):
        """
        Validate and do what ever is needed to store the
        current item instance to a storage.
        """
        # Before writing data back, validate myself
        self._validate()

    def _validate(self):
        """
        Validate item. Checks for mandatory properties. Raises
        ref:`python:ValueError` on failure.
        """
        # pylint: disable-msg=E1101
        for opt, data in self._options.iteritems():
            if data['required'] and not data['value']:
                raise ValueError("item '%s' is mandatory" % opt)

    def scan(self):
        """
        Scans the configured path for items of the current type and
        returns a dictionary with filename/absolute path mappings.

        ``Return:`` dict
        """
        return {}

    def getAssignableElements(self):
        """
        Returns items that are assignable to a device. The result is
        represented by a dict index by the *item name* containing these keys:

        =========== =========================
        Key         Description
        =========== =========================
        description Item description
        parameter   Available item parameters
        =========== =========================

        ``Return:`` dict
        """
        return {}
