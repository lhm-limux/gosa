# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: util.py 530 2010-08-12 07:47:05Z cajus $$

 This is the environment container of the GOsa AMQP agent. This environment
 contains all stuff which may be relevant for plugins and the core. Its
 reference gets passed to all plugins.

 See LICENSE for more information about the licensing.
"""
from string import *


def isMailAddress(addr):
    """
    Validate mail address against rfc822.

    @type addr: string
    @param addr: mail address

    @rtype: bool
    @return: True if address validates


    Ported from Recipe 3.9 in Secure Programming Cookbook for C and C++ by
    John Viega and Matt Messier (O'Reilly 2003)
    """
    rfc822_specials = '()<>@,;:\\"[]'

    # First we validate the name portion (name@domain)
    c = 0
    while c < len(addr):
        if addr[c] == '"' and (not c or addr[c - 1] == '.' or addr[c - 1] == '"'):
            c = c + 1
            while c < len(addr):
                if addr[c] == '"':
                    break
                if addr[c] == '\\' and addr[c + 1] == ' ':
                    c = c + 2
                    continue
                if ord(addr[c]) < 32 or ord(addr[c]) >= 127:
                    return False
                c = c + 1
            else:
                return False

            if addr[c] == '@':
                break

            if addr[c] != '.':
                return False

            c = c + 1
            continue

        if addr[c] == '@':
            break

        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False

        if addr[c] in rfc822_specials:
            return False

        c = c + 1

    if not c or addr[c - 1] == '.':
        return False

    # Next we validate the domain portion (name@domain)
    domain = c = c + 1
    if domain >= len(addr):
        return False
    count = 0
    while c < len(addr):
        if addr[c] == '.':
            if c == domain or addr[c - 1] == '.':
                return False
            count = count + 1
        if ord(addr[c]) <= 32 or ord(addr[c]) >= 127:
            return False
        if addr[c] in rfc822_specials:
            return False
        c = c + 1

    return count >= 1
