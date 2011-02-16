#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gosa.common.components.jsonrpc_proxy import JSONServiceProxy

# Create connection to service
proxy = JSONServiceProxy('https://amqp.intranet.gonicus.de:8080/rpc')
proxy.login("admin", "secret")

# List methods
print proxy.getMethods()

# Create samba password hash
print proxy.mksmbhash("secret")
