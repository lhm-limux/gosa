Base install modules
====================

The base install modules are used to do the basic bootstrapping of
devices. Methods coming into mind should work template based
(configuration file) and may be something like *preseed*, *kickstart*, *fai* or
*autoyast*.

---------------

.. autoclass:: libinst.interface.BaseInstallMethod
   :members:

Disk definition
===============

The disk definition acts as a proxy between the encoding of
partition schemes. While defining partitions on the object,
you can get the output needed for preseed, kickstart or what
ever you like to implement.

---------------

.. autoclass:: libinst.interface.DiskDefinition
   :members:
