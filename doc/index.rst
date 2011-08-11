Welcome to GOsa's documentation!
================================

What is it all about?
---------------------

If you get here, you probably know that GOsa (currently) is a PHP based framework
for managing several aspects of your infrastructure. For more information, please
go to the `GOsa Website <https://oss.gonicus.de/labs/gosa>`_.

While you can find information about the GOsa 2.x series on the website mentioned
above, this document is more about the future. This is why:

Starting with GOsa 2.6, we had introduced a simple perl based service called
gosa-si, which was able to handle requests and actions where class PHP applications
are not well suited for. This service had (has) many problems in design, scalability
and so on. For that reason we started to redo the whole thing using new
technologies like `AMQP <http://www.amqp.org>`_, concentrating on the RedHat/Apache
implementation `QPID <http://qpid.apache.org/>`_.

This service handles the *authentication*, the *message queueing*, the *clustering* and
*load balancing* for us. A client can subscribe to public events using
`XQuery <http://en.wikipedia.org/wiki/XQuery>`_, services (or third parties) can
emit events in a simple manner. AMQP is used by the newly introduced *GOsa agent*
to provide load balanced, clustered services and by several kind of *GOsa client*
applications like a shell, an ordinary client (former GOto clients) and so on.

Multiple *GOsa agents* create a domain where clients can join or participate in
different ways. Functionality like the new abstraction layer *libinst*, an object
description language, scheduling, etc. are spread over several agents and can be
transparently accessed by clients, thanks to the routing possible with QPID queue
models. The functionality is currently exposed by AMQP and by a HTTP/JSONRPC gateway,
more methods like ReST or SOAP may follow if there's an urgent need for that.

Starting with PHP GOsa 2.7, there is built in support for the new GOsa core. 2.7
series will be some kind of migration series where more and more functionality will
be moved into the new core while keeping the original functionality inside. That
allows *bleeding edge* users to try selected new functionality thru the new core and
more *conservative* users can continue to use the current PHP core.

The 3.0 release will be a PHP-GOsa with nearly no functionality residing in PHP, but
in the new core. And - finally - this documentation is growing on the way to 3.0.

.. warning::

   This is **pre-alpha** software and you're welcome to try, code and share with us.

---------------------

Topics:

.. toctree::
   :maxdepth: 2

   intro
   common/index
   agent/index
   client/index
   shell/index
   plugins/index
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

