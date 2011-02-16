#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: event.py 279 2010-06-29 15:22:34Z cajus $$

 This is the Event object. It constructs events to be sent thru the
 org.gosa.event topics.

 See LICENSE for more information about the licensing.

 Warning: This is a hack. Looks like we've to code an own
 d-i module to do proper partitioning. The partman implementation
 doesn't seem to be well fitted for creating well defined
 partition layouts.
"""
import re
from methods.preseed import DebianDiskDefinition, LINUX, ALL


def main():
    dd = DebianDiskDefinition()
    dd.addDisk('sda', removeParts=ALL)

    #Test 1
    dd.addPartition("/boot", size=250, onDisk='sda', boot=True, fsType="ext3", primary=True)
    dd.addPartition("/", size=4000, onDisk='sda', fsType="ext3", primary=True)
    dd.addPartition("swap", size=4000, onDisk='sda', primary=True)
    dd.addPartition("/usr", size=5000, onDisk='sda', fsType="ext3", primary=False)
    dd.addPartition("/srv", size=10000, grow=True, fsType="ext3", onDisk='sda', primary=False)
    dd.addPartition("/var", size=5000, onDisk='sda', fsType="ext3", primary=False)

    #Test 2
    #dd.addPartition("/boot", size=250, onDisk='sda', boot=True, fsType="ext3", primary=True)
    #dd.addPartition("pv.01", size=40000, grow=True, onDisk='sda', primary=True)
    #dd.addVolumeGroup("system", ["pv.01"])
    #dd.addVolume("/", size=4000, volGroup='system', fsType="ext3", name="root")
    #dd.addVolume("swap", size=4000, volGroup='system', name="swap")
    #dd.addVolume("/usr", size=5000, volGroup='system', fsType="ext3", name="usr")
    #dd.addVolume("/srv", size=10000, grow=True, volGroup='system', fsType="ext3", name="srv")
    #dd.addVolume("/var", size=4000, volGroup='system', fsType="ext3", name="var")
    #dd.addVolume("/home", size=10000, volGroup='system', fsType="ext3", name="home")

    #dd.addPartition("raid.11", size=1000, onDisk='sda', primary=True)
    #dd.addPartition("raid.12", size=1000, onDisk='sda', primary=True)
    #dd.addPartition("raid.21", size=1000, onDisk='sda', primary=False)
    #dd.addPartition("raid.22", size=1000, onDisk='sda', primary=False)
    #dd.addPartition("/", size=1000, onDisk='hda', fsType="ext3", primary=True)
    #dd.addPartition("pv.02", size=1000, onDisk='hda', fsType="ext3", primary=False)
    #dd.addRaidDevice("/safe", name="md1", fsType="ext3", level="1", devices=["raid.11", "raid.12"])
    #dd.addRaidDevice("pv.01", name="md0", fsType="ext3", level="1", devices=["raid.21", "raid.22"])
    #dd.addVolumeGroup("sysvg", ["pv.01", "pv.02"])
    #dd.addVolume("/mnt", size=8000, name="voltest", fsType="ext3", volGroup="sysvg")
    #dd.addVolume("swap", size=8000, name="swapvol", volGroup="sysvg")

    print(dd.dump())
    #print dd

if __name__ == '__main__':
    main()
