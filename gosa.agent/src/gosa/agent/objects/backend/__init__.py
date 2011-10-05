# -*- coding: utf-8 -*-
__import__('pkg_resources').declare_namespace(__name__)
import re

class EntryNotUnique(Exception):
    pass


class EntryNotFound(Exception):
    pass


class ObjectBackend(object):
    _is_uuid = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')

    def dn2uuid(self, dn):
        """
        Convert DN to uuid.
        """
        raise NotImplementedError("object backend is not capable of mapping DN to UUID")

    def load(self, uuid, keys):
        """
        Load given keys from entry with uuid.
        """
        raise NotImplementedError("object backend is missing load()")

    def move(self, uuid, new_base):
        """
        Move object to new base.
        """
        raise NotImplementedError("object backend is not capable of moving objects")

    def create(self, dn, data, params):
        """
        Create a new base object entry with the given DN.
        """
        raise NotImplementedError("object backend is not capable of creating base objects")

    def extend(self, uuid, data, params):
        """
        Create an extension to a base object with the given UUID.
        """
        raise NotImplementedError("object backend is not capable of creating object extensions")

    def update(self, uuid, data):
        """
        Update a base entry or an extension with the given UUID.
        """
        raise NotImplementedError("object backend is missing update()")

    def exists(self, misc):
        """
        Check if an object with the given UUID or DN exists.
        """
        raise NotImplementedError("object backend is missing exists()")

    def remove(self, uuid):
        """
        Remove base object specified by UUID.
        """
        raise NotImplementedError("object backend is missing remove()")

    def retract(self, uuid):
        """
        Retract extension from base object specified by UUID.
        """
        raise NotImplementedError("object backend is missing retract()")

    def is_uuid(self, uuid):
        return bool(self._is_uuid.match(uuid))

    def is_uniq(self, attr, value):
        """
        Check if the given attribute is unique.
        """
        raise NotImplementedError("object backend is missing retract()")
