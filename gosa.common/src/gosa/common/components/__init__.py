"""
The compoments module gathers a couple of common components that are of
use for both agents and clients.
"""
__import__('pkg_resources').declare_namespace(__name__)
from gosa.common.components.amqp_proxy import AMQPServiceProxy
from gosa.common.components.amqp_proxy import AMQPEventConsumer
from gosa.common.components.amqp_proxy import AMQPStandaloneWorker
from gosa.common.components.objects import ObjectRegistry
from gosa.common.components.amqp import AMQPHandler
from gosa.common.components.amqp import AMQPWorker
from gosa.common.components.amqp import AMQPProcessor
from gosa.common.components.amqp import EventProvider
from gosa.common.components.amqp import EventConsumer
from gosa.common.components.command import Command
from gosa.common.components.command import CommandInvalid
from gosa.common.components.command import CommandNotAuthorized
from gosa.common.components.dbus_runner import DBusRunner
from gosa.common.components.jsonrpc_proxy import JSONRPCException
from gosa.common.components.jsonrpc_proxy import ObjectFactory
from gosa.common.components.jsonrpc_proxy import JSONServiceProxy
from gosa.common.components.plugin import Plugin
from gosa.common.components.registry import PluginRegistry
from gosa.common.components.zeroconf_client import ZeroconfClient
from gosa.common.components.zeroconf import ZeroconfService
