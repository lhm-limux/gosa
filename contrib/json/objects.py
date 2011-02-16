# -*- coding: utf-8 -*-

class User(object):
    # Presets
    __sn = None
    __givenName = None
    __uid = None
    __telephoneNumber = None

    # SN
    @property
    def sn(self):
        return self.__sn

    @sn.setter
    def sn(self, value):
        self.__sn = value

    @sn.deleter
    def sn(self):
        self.__sn = None


    # UID
    @property
    def uid(self):
        return self.__uid

    @uid.setter
    def uid(self, value):
        self.__uid = value

    @uid.deleter
    def uid(self):
        self.__uid = None


    # GIVENNAME
    @property
    def givenName(self):
        return self.__givenName

    @givenName.setter
    def givenName(self, value):
        self.__givenName = value

    @givenName.deleter
    def givenName(self):
        self.__givenName = None


    # TELEPHONENUMBER
    @property
    def telephoneNumber(self):
        return self.__telephoneNumber

    @telephoneNumber.setter
    def telephoneNumber(self, value):
        self.__telephoneNumber = value

    @telephoneNumber.deleter
    def telephoneNumber(self):
        self.__telephoneNumber = None


    # METHODS
    def notify(self):
        return True

    def remove(self):
        return False

    def setPassword(self, password):
        print "Password:", password
        return False

