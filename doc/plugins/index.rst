Plugin development
==================

Basically there are four plugin types that are used inside of GOsa. Two of
them are *agent* plugins - namely handlers and ordinary plugins, one flavor
of *client* plugins and one flavor of *dbus* plugins.

.. _plugins:

In order to help with quick plugin templating, there's a helper script **tools/gosa-plugin-skel**
which asks a couple of questions and generates a quickstart for you::

  $ tools/gosa-plugin-skel
  Generate plugin skeleton. Please provide some information:
  
  Plugin name (must be [a-z][a-z0-9]+): sample
  Plugin type (agent, client, dbus): agent
  Version: 1.0
  Authors name: Cajus Pollmeier
  Authors email: pollmeier@gonicus.de

  Done. Please check out the 'sample' directory.
  $

Here's the resulting directory structure::

  $ find sample
  sample
  sample/README
  sample/setup.cfg
  sample/setup.py
  sample/src
  sample/src/gosa
  sample/src/gosa/__init__.py
  sample/src/gosa/agent
  sample/src/gosa/agent/__init__.py
  sample/src/gosa/agent/plugins
  sample/src/gosa/agent/plugins/__init__.py
  sample/src/gosa/agent/plugins/sample
  sample/src/gosa/agent/plugins/sample/locale
  sample/src/gosa/agent/plugins/sample/__init__.py
  sample/src/gosa/agent/plugins/sample/tests
  sample/src/gosa/agent/plugins/sample/main.py

**Topics:**

.. toctree::
   :maxdepth: 2

   agent/index
   client/index
   dbus/index

Plugins
=======

This section contains documentation for available GOsa plugins. These may
come as standalone plugins or may be included in the core GOsa modules.
If you find missing plugins, please send patches to these documentation files.

Agent plugins
-------------

.. toctree::
   :maxdepth: 2

   agent/goto
   agent/gravatar
   agent/libinst
   agent/misc
   agent/samba

Client plugins
--------------

.. toctree::
   :maxdepth: 2

   agent/goto
   agent/libinst


DBUS plugins
------------

.. toctree::
   :maxdepth: 2

   agent/goto
   agent/libinst
