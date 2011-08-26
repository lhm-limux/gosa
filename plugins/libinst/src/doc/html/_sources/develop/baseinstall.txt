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

Here's a basic usage sample from the gosa-shell::

	>>> o = gosa.openObject('libinst.preseed.diskdefinition')
	>>> o.dump()
	''
	>>> o.addDisk('sda')
	>>> o.addPartition("/boot", 250, None, False, True, True, True, 'ext3', None, False, None, 'sda')
	>>> o.addPartition("pv.01", 10000, None, True, True, False, False, None, None, False, None, 'sda')
	>>> o.addVolumeGroup("system", ["pv.01"])
	>>> o.addVolume("/", "root", "system", 4000, None, False, True, False, "ext3")
	>>> o.addVolume("swap", "swap", "system", 4000)
	>>> o.addVolume("/usr", "usr", "system", 1000, None, False, True, False, "ext3")
	>>> o.getDisks()
	[{u'device': u'sda', u'initlabel': True, u'removeParts': None}]
	>>> o.dump()
	u'disk sda --initlabel --none;part /boot --size 250 --format --bootable --asprimary --fstype ext3 --ondisk sda;part pv.01 --size 10000 --grow --format --ondisk sda;volgroup system --format pv.01;logvol / --size 4000 --format --fstype ext3 --name root --vgname system;logvol swap --size 4000 --format --name swap --vgname system;logvol /usr --size 1000 --format --fstype ext3 --name usr --vgname system;'
	>>> o.getDeviceUsage()
	{u'disk': {u'sda': {u'usage': 10250, u'size': 20000}, u'sdb': {u'usage': 0, u'size': 100000}}, u'part': {u'pv.01': {u'size': 10000}, u'/boot': {u'size': 250}}, u'raid': {}, u'vg': {u'system': {u'usage': 9000, u'size': 10000}}}
	>>> gosa.closeObject(str(o))

---------------

.. autoclass:: libinst.interface.DiskDefinition
   :members:
