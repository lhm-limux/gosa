# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: network.py 1208 2010-10-21 11:40:16Z cajus $$

 This plugin is part of the GOto functionality. It provides
 helper to handle machines.

 See LICENSE for more information about the licensing.
"""
import socket
import dumbnet
import re
from telnetlib import Telnet
from netaddr import *

from gosa.common.components.plugin import Plugin
from gosa.common.utils import N_
from gosa.common.env import Environment
from gosa.common.components.command import Command, FIRSTRESULT


class NetworkUtils(Plugin):
    """
    Module containing network utilities like DNS/MAC resolving and
    manufacturer resolving.
    """
    _target_ = 'goto'
    oui = None

    def __init__(self):
        env = Environment.getInstance()

    @Command(type=FIRSTRESULT, __doc__=N_("Resolve network address to a mac / dns name tupel."))
    def networkCompletion(self, name):
        protocolAddress = socket.gethostbyname(name)
        networkAddress = self.getMacFromIP(protocolAddress)
        return {'ip': protocolAddress, 'mac': networkAddress }

    def __sendPacket(self, protocolAddress):
        try:
            tn = Telnet(protocolAddress, 139, 1)
            tn.close()
        except:
            pass

    def getMacFromARP(self, protocolAddress):
        arp = dumbnet.arp()
        return arp.get(dumbnet.addr(protocolAddress))

    def getMacFromIP(self, protocolAddress):
        result = self.getMacFromARP(protocolAddress)
        if not result:
            self.__sendPacket(protocolAddress)
            result = self.getMacFromARP(protocolAddress)
        return str(result)

    """ This function uses the ieee file provided at
        http://standards.ieee.org/regauth/oui/oui.txt """
    @Command(__doc__=N_("Resolve mac address to the producer of the"+
        " network card if possible."))
    def getMacManufacturer(self, mac):
        try:
            mac = EUI(mac)
            oui = mac.oui.registration()
        except NotRegisteredError:
            return None
        # pylint: disable-msg=E1101
        return oui.org
