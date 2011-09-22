# -*- coding: utf-8 -*-
import re
import os
import string
import random
import hashlib
import ldap
import time
import datetime
import types
import logging
from threading import Timer
from zope.interface import implements
from gosa.common.components.jsonrpc_proxy import JSONRPCException
from qpid.messaging import uuid4

from gosa.common.handler import IInterfaceHandler
from gosa.common.event import EventMaker
from gosa.common import Environment
from gosa.common.utils import stripNs, N_
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.amqp import EventConsumer
from gosa.common.components import AMQPServiceProxy, Plugin
from gosa.common.components.command import Command
from gosa.agent.ldap_utils import LDAPHandler
from base64 import encodestring as encode
from Crypto.Cipher import AES

STATUS_SYSTEM_ON = "O"
STATUS_UPDATABLE = "u"
STATUS_UPDATING = "U"
STATUS_INVENTORY = "i"
STATUS_CONFIGURING = "C"
STATUS_INSTALLING = "I"
STATUS_VM_INITIALIZING = "V"
STATUS_WARNING = "W"
STATUS_ERROR = "E"
STATUS_OCCUPIED = "B"
STATUS_LOCKED = "L"
STATUS_BOOTING = "b"
STATUS_NEEDS_INITIAL_CONFIG = "P"
STATUS_NEEDS_REMOVE_CONFIG = "R"
STATUS_NEEDS_CONFIG = "c"
STATUS_NEEDS_INSTALL = "N"


class ClientService(Plugin):
    """
    Plugin to register clients and expose their functionality
    to the users.
    """
    implements(IInterfaceHandler)
    _priority_ = 90
    _target_ = 'goto'
    __client = {}
    __proxy = {}
    __user_session = {}


    def __init__(self):
        """
        Construct a new ClientService instance based on the configuration
        stored in the environment.
        """
        env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.log.debug("initializing client service")
        self.env = env
        self.__cr = None

    def serve(self):
        # Add event processor
        amqp = PluginRegistry.getInstance('AMQPHandler')
        EventConsumer(self.env,
            amqp.getConnection(),
            xquery="""
                declare namespace f='http://www.gonicus.de/Events';
                let $e := ./f:Event
                return $e/f:ClientAnnounce
                    or $e/f:ClientLeave
                    or $e/f:UserSession
            """,
            callback=self.__eventProcessor)

        # Get registry - we need it later on
        self.__cr = PluginRegistry.getInstance("CommandRegistry")

        # Start maintainence timer
        timer = Timer(10.0, self.__refresh)
        timer.start()
        self.env.threads.append(timer)

    def __refresh(self):
        # Initially check if we need to ask for client caps or if there's someone
        # who knows...
        if not self.__client:
            nodes = self.__cr.getNodes()
            if not nodes:
                return

            # If we're alone, please clients to announce themselves
            if len(nodes) == 1 and self.env.id in nodes:
                amqp = PluginRegistry.getInstance('AMQPHandler')
                e = EventMaker()
                amqp.sendEvent(e.Event(e.ClientPoll()))

            # Elseways, ask other servers for more client info
            else:
                #TODO: get from host
                #take a random node and:
                # ... for all clients
                #     ... load client capabilities and store them localy
                raise Exception("getting client information from other nodes is not implmeneted!")

        #TODO: check for old clients
        # Register some task at the scheduler for that

    def stop(self):
        pass

    @Command(__help__=N_("List available clients."))
    def getClients(self):
        """
        TODO
        """
        res = {}
        for uuid, info in self.__client.iteritems():
            res[uuid] = {'name':info['name'], 'received':info['received']}
        return res

    @Command(__help__=N_("Call method exposed by client."))
    def clientDispatch(self, client, method, *arg, **larg):
        """
        TODO
        """

        # Bail out if the client is not available
        if not client in self.__client:
            raise JSONRPCException("client '%s' not available" % client)

        # Generate tage queue name
        queue = '%s.client.%s' % (self.env.domain, client)
        self.log.debug("got client dispatch: '%s(%s)', sending to %s" % (method, arg, queue))

        # client queue -> amqp rpc proxy
        if not client in self.__proxy:
            amqp = PluginRegistry.getInstance("AMQPHandler")
            self.__proxy[client] = AMQPServiceProxy(amqp.url['source'], queue)

        # Call her to the moon...
        methodCall = getattr(self.__proxy[client], method)

        # Do the call
        res = methodCall(*arg, **larg)
        return res

    @Command(__help__=N_("Get the client Interface/IP/Netmask/Broadcast/MAC list."))
    def getClientNetInfo(self, client):
        """
        TODO
        """
        if not client in self.__client:
            return []

        res = self.__client[client]['network']
        return res

    @Command(__help__=N_("List available client methods for specified client."))
    def getClientMethods(self, client):
        """
        TODO
        """
        if not client in self.__client:
            return []

        return self.__client[client]['caps']

    @Command(__help__=N_("List user sessions per client"))
    def getUserSessions(self, client=None):
        """
        TODO
        """
        if client:
            return self.__user_session[client] if client in self.__user_session else []

        return self.__user_session

    @Command(__help__=N_("List clients a user is logged in"))
    def getUserClients(self, user):
        """
        TODO
        """
        return [client for client, users in self.__user_session.items() if user in users]

    @Command(__help__=N_("Send synchronous notification message to user"))
    def notifyUser(self, users, title, message, timeout=10, level='normal', icon='dialog-information'):
        """
        TODO
        """
        if users:
            # Notify a single / group of users
            if type(users) != types.ListType:
                users = [users]

            for user in users:
                for client in self.getUserClients(user):
                    try:
                        self.clientDispatch(client, "notify", user, title, message,
                                timeout, level, icon)
                    #pylint: disable=W0141
                    except Exception:
                        pass

        else:
            # Notify all users
            for client in self.__client.keys():
                try:
                    self.clientDispatch(client, "notify_all", title, message,
                            timeout, level, icon)
                #pylint: disable=W0141
                except Exception:
                    pass

    @Command(__help__=N_("Set system status"))
    def systemGetStatus(self, device_uuid):
        """
        TODO
        """
        lh = LDAPHandler.get_instance()
        fltr = "deviceUUID=%s" % device_uuid

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=device)(%s))" % fltr, ['deviceStatus'])

            if len(res) != 1:
                raise ValueError("no device '%s' available" % device_uuid)

            return res[0][1]["deviceStatus"][0]

        return ""

    @Command(__help__=N_("Set system status"))
    def systemSetStatus(self, device_uuid, status):
        """
        TODO
        """
        # Check params
        valid = [STATUS_SYSTEM_ON, STATUS_LOCKED, STATUS_UPDATABLE,
            STATUS_UPDATING, STATUS_INVENTORY, STATUS_CONFIGURING,
            STATUS_INSTALLING, STATUS_VM_INITIALIZING, STATUS_WARNING,
            STATUS_ERROR, STATUS_OCCUPIED, STATUS_BOOTING,
            STATUS_NEEDS_INSTALL, STATUS_NEEDS_CONFIG,
            STATUS_NEEDS_INITIAL_CONFIG, STATUS_NEEDS_REMOVE_CONFIG]

        # Write to LDAP
        lh = LDAPHandler.get_instance()
        fltr = "deviceUUID=%s" % device_uuid

        with lh.get_handle() as conn:
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=device)(%s))" % fltr, ['deviceStatus'])

            if len(res) != 1:
                raise ValueError("no device '%s' available" % device_uuid)

            devstat = res[0][1]['deviceStatus'][0] if 'deviceStatus' in res[0][1] else ""
            is_new = not bool(devstat)
            devstat = list(devstat.strip("[]"))

            r = re.compile(r"([+-].)")
            for stat in r.findall(status):
                if not stat[1] in valid:
                    raise ValueError("invalid status %s" % stat[1])
                if stat.startswith("+"):
                    if not stat[1] in devstat:
                        devstat.append(stat[1])
                else:
                    if stat[1] in devstat:
                        devstat.remove(stat[1])

            devstat = "[" + "".join(devstat).encode('utf8') + "]"
            if is_new:
                conn.modify(res[0][0], [(ldap.MOD_ADD, "deviceStatus", [devstat])])
            else:
                conn.modify(res[0][0], [(ldap.MOD_REPLACE, "deviceStatus", [devstat])])

    @Command(needsUser=True,__help__=N_("Join a client to the GOsa system."))
    def joinClient(self, user, device_uuid, mac, info=None):
        """
        TODO
        """
        uuid_check = re.compile(r"^[0-9a-f]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE)
        if not uuid_check.match(device_uuid):
            raise ValueError("join with invalid UUID %s" % device_uuid)

        lh = LDAPHandler.get_instance()

        # Handle info, if present
        more_info = []

        if info:
            # Check string entries
            for entry in filter(lambda x: x in info,
                ["serialNumber", "ou", "o", "l", "description"]):

                if not re.match(r"^[\w\s]+$", info[entry]):
                    raise ValueError("invalid data (%s) provided for '%s'" % (info[entry], entry))

                more_info.append((entry, info[entry]))

            # Check desired device type if set
            if "deviceType" in info:
                if re.match(r"^(terminal|workstation|server|sipphone|switch|router|printer|scanner)$",
                    info["deviceType"]):

                    more_info.append(("deviceType", info["deviceType"]))
                else:
                    raise ValueError("invalid device type '%s' specified" % info["deviceType"])

            # Check owner for presence
            if "owner" in info:
                with lh.get_handle() as conn:

                    # Take a look at the directory to see if there's
                    # such an owner DN
                    try:
                        conn.search_s(info["owner"], ldap.SCOPE_BASE, attrlist=['dn'])
                        more_info.append(("owner", info["owner"]))
                    except Exception as e:
                        raise ValueError("owner %s not found: %s" % (info["owner"], str(e)))

        # Generate random client key
        random.seed()
        key = ''.join(random.Random().sample(string.letters + string.digits, 32))
        salt = os.urandom(4)
        h = hashlib.sha1(key)
        h.update(salt)

        # Do LDAP operations to add the system
        with lh.get_handle() as conn:

            # Take a look at the directory to see if there's
            # already a joined client with this uuid
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                "(&(objectClass=registeredDevice)(macAddress=%s))" % mac, ["macAddress"])

            # Already registered?
            if res:
                raise Exception("device with hardware address %s has already been joined" % mac)

            # While the client is going to be joined, generate a random uuid and
            # an encoded join key
            cn = str(uuid4())
            device_key = self.__encrypt_key(device_uuid.replace("-", ""), cn + key)

            # Resolve manger
            res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                    "(uid=%s)" % user, [])
            if len(res) != 1:
                raise Exception("failed to get current users DN: %s" %
                    ("not unique" if res else "not found"))
            manager = res[0][0]

            # Create new machine entry
            record = [
                ('objectclass', ['device', 'ieee802Device', 'simpleSecurityObject', 'registeredDevice']),
                ('deviceUUID', cn),
                ('deviceKey', [device_key]),
                ('cn', [cn] ),
                ('manager', [manager] ),
                ('macAddress', [mac.encode("ascii", "ignore")] ),
                ('userPassword', ["{SSHA}" + encode(h.digest() + salt)])
            ]
            record += more_info

            # Evaluate base
            #TODO: take hint from "info" parameter, to allow "joiner" to provide
            #      a target base
            base = lh.get_base()

            # Add record
            dn = ",".join(["cn=" + cn, self.env.config.get("goto.machine-rdn",
                default="ou=systems"), base])
            conn.add_s(dn, record)

        self.log.info("UUID '%s' joined as %s" % (device_uuid, dn))
        return [key, cn]

    def __encrypt_key(self, key, data):
        """
        Encrypt a data using key
        """

        # Calculate padding length
        key_pad = AES.block_size - len(key) % AES.block_size
        data_pad = AES.block_size - len(data) % AES.block_size

        # Pad data PKCS12 style
        if key_pad != AES.block_size:
            key += chr(key_pad) * key_pad
        if data_pad != AES.block_size:
            data += chr(data_pad) * data_pad

        return AES.new(key, AES.MODE_ECB).encrypt(data)

    def __eventProcessor(self, data):
        eventType = stripNs(data.xpath('/g:Event/*', namespaces={'g': "http://www.gonicus.de/Events"})[0].tag)
        func = getattr(self, "_handle" + eventType)
        func(data)

    def _handleUserSession(self, data):
        data = data.UserSession
        self.log.debug("updating client '%s' user session information" % data.Id)
        if hasattr(data.User, 'Name'):
            self.__user_session[str(data.Id)] = map(str, data.User.Name)
            self.systemSetStatus(str(data.Id), "+B")
        else:
            self.__user_session[str(data.Id)] = []
            self.systemSetStatus(str(data.Id), "-B")

    def _handleClientAnnounce(self, data):
        data = data.ClientAnnounce
        client = data.Id.text
        self.log.debug("client '%s' is joining us" % client)
        self.systemSetStatus(client, "+O")

        # Remove remaining proxy values for this client
        if client in self.__proxy:
            self.__proxy[client].close()
            del self.__proxy[client]

        # Assemble caps
        caps = {}
        for method in data.ClientCapabilities.ClientMethod:
            caps[method.Name.text] = {
                'path': method.Path.text,
                'sig': method.Signature.text,
                'doc': method.Documentation.text}

        # Assemble network information
        network = {}
        for interface in data.NetworkInformation.NetworkDevice:
            network[interface.Name.text] = {
                'IPAddress': interface.IPAddress.text,
                'IPv6Address': interface.IPv6Address.text,
                'MAC': interface.MAC.text,
                'Netmask': interface.Netmask.text,
                'Broadcast': interface.Broadcast.text}

        # Add recieve time to be able to sort out dead nodes
        t = datetime.datetime.utcnow()
        info = {
            'name': data.Name.text,
            'received': time.mktime(t.timetuple()),
            'caps': caps,
            'network': network
        }

        self.__client[data.Id.text] = info

        # Handle pending "P"repare actions for that client
        if "P" in self.systemGetStatus(client):
            try:
                rm = PluginRegistry.getInstance("RepositoryManager")
                rm.prepareClient(client)
            except ValueError:
                pass

    def _handleClientLeave(self, data):
        data = data.ClientLeave
        client = data.Id.text
        self.log.debug("client '%s' is leaving" % client)
        self.systemSetStatus(client, "-O")

        if client in self.__client:
            del self.__client[client]

        if client in self.__proxy:
            self.__proxy[client].close()
            del self.__proxy[client]

        if client in self.__user_session:
            del self.__user_session[client]
