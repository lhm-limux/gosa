# -*- coding: utf-8 -*-
import socket
import dumbnet
from netaddr import EUI, NotRegisteredError
from telnetlib import Telnet

from gosa.common.components import Plugin
from gosa.common.utils import N_
from gosa.common.components.command import Command, FIRSTRESULT


class NetworkUtils(Plugin):
    """
    Module containing network utilities like DNS/MAC resolving and
    manufacturer resolving.
    """
    _target_ = 'goto'
    oui = None

    @Command(type=FIRSTRESULT, __help__=N_("Resolve network address to a mac / dns name tupel."))
    def networkCompletion(self, name):
        """
        TODO
        """
        protocolAddress = socket.gethostbyname(name)
        networkAddress = self.getMacFromIP(protocolAddress)
        return {'ip': protocolAddress, 'mac': networkAddress }

    def __sendPacket(self, protocolAddress):
        try:
            tn = Telnet(protocolAddress, 139, 1)
            tn.close()
        except Exception:
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

    @Command(__help__=N_("Resolve mac address to the producer of the"+
        " network card if possible."))
    def getMacManufacturer(self, mac):
        """
        This function uses the ieee file provided at
        http://standards.ieee.org/regauth/oui/oui.txt

        TODO
        """
        try:
            mac = EUI(mac)
            oui = mac.oui.registration()
        except NotRegisteredError:
            return None
        # pylint: disable=E1101
        return oui.org
