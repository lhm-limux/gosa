# -*- coding: utf-8 -*-
"""
The *common* library bundles a couple of shared resources that are needed
by more than one component. It also includes base XML data which is required
for over all schema checking.

Here is an example on how to use the common module::

    >>> from gosa.common import Environment
    >>> env = Environment.getInstance()

This loads the GOsa environment information using the Environment singleton.

.. note::

    Using the environment requires the presence of the GOsa configuration
    file - commonly ``~/.gosa/config`` or ``/etc/gosa/config`` in this
    order
"""

__version__ = __import__('pkg_resources').get_distribution('gosa.common').version
__import__('pkg_resources').declare_namespace(__name__)

from gosa.common.env import Environment
