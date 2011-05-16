# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2010, 2011 GONICUS GmbH

 See LICENSE for more information about the licensing.
"""
import re
import itertools
from gosa.common.components.registry import PluginRegistry

LINUX = 2 ** 0
ALL = 2 ** 1


class DiskDefinition(object):
    supportedFsTypes = []
    supportedRaidLevels = [0, 1, 5]
    supportedDeviceTypes = []
    supportEncryption = False

    def __init__(self, definition=None):
        self._disks = []
        self._parts = []
        self._raids = []
        self._volgroups = []
        self._vols = []

        if definition:
            self._parseDiskDefinition(definition)

    def _optionIterator(self, source):
        for pattern in source:
            yield(pattern)

    def _parseOption(self, source, target, option, key=None, value=None,
            default=None, numeric=False):
        target[key if key else option] = default
        pattern = self._optionIterator(source)
        try:
            # Look for the specified option in
            while True:
                if pattern.next() == "--" + option:
                    val = value if value else pattern.next()
                    if numeric:
                        val = int(val)
                    target[key if key else option] = val
                    idx = source.index("--" + option)
                    if not value:
                        del source[idx + 1]
                    del source[idx]
                    break
        except StopIteration:
            pass

    def _parseDiskDefinition(self, data):

        entries = data.split(';')
        for entry in entries:
            # Skip empty entries that might be produced by additional
            # ; elements
            if not entry:
                continue

            # Replace multiple spaced by one and split to single tokens
            entry = entry.split()
            entryType = entry[0]

            # Parse disk
            if entryType == "disk":
                disk = {}

                # Handle initlabel
                self._parseOption(entry, disk, 'initlabel', 'initlabel', True)
                self._parseOption(entry, disk, 'all', 'removeParts', ALL)
                self._parseOption(entry, disk, 'none', 'removeParts', None)
                self._parseOption(entry, disk, 'linux', 'removeParts', LINUX)

                disk['device'] = entry[1]
                self._disks.append(disk)
                continue

            # Parse partition
            if entryType == "part":
                part = {}
                self._parseOption(entry, part, 'size', numeric=True)
                self._parseOption(entry, part, 'maxsize', 'maxSize', numeric=True)
                self._parseOption(entry, part, 'grow', 'grow', True)
                self._parseOption(entry, part, 'encrypted', 'encrypted', True)
                self._parseOption(entry, part, 'passphrase')
                self._parseOption(entry, part, 'format', 'format', True)
                self._parseOption(entry, part, 'bootable', 'bootable', True)
                self._parseOption(entry, part, 'asprimary', 'primary', True)
                self._parseOption(entry, part, 'fstype', 'fsType')
                self._parseOption(entry, part, 'fsoptions', 'fsOptions')
                self._parseOption(entry, part, 'ondisk', 'onDisk')
                part['target'] = entry[1]
                self._parts.append(part)
                continue

            # Parse raid device
            if entryType == "raid":
                raid = {}
                self._parseOption(entry, raid, 'level', numeric=True)
                self._parseOption(entry, raid, 'name')
                self._parseOption(entry, raid, 'spares', numeric=True)
                self._parseOption(entry, raid, 'format', 'format', True)
                self._parseOption(entry, raid, 'useexisting', 'useExisting', True)
                self._parseOption(entry, raid, 'ondisk', 'onDisk')

                raid['target'] = entry[1]
                raid['devices'] = entry[2:]
                raid['device'] = raid['name']
                self._raids.append(raid)
                continue

            # Parse volume group
            if entryType == "volgroup":
                volgroup = {}

                self._parseOption(entry, volgroup, 'pesize', 'peSize', numeric=True)
                self._parseOption(entry, volgroup, 'format', 'format', True)
                self._parseOption(entry, volgroup, 'useexisting', 'useExisting', True)

                volgroup['name'] = entry[1]
                volgroup['device'] = volgroup['name']
                volgroup['partitions'] = entry[2:]

                self._volgroups.append(volgroup)
                continue

            # Parse volume
            if entryType == "logvol":
                vol = {}

                self._parseOption(entry, vol, 'format', 'format', True)
                self._parseOption(entry, vol, 'useexisting', 'useExisting', True)
                self._parseOption(entry, vol, 'size', numeric=True)
                self._parseOption(entry, vol, 'maxsize', 'maxSize', numeric=True)
                self._parseOption(entry, vol, 'grow', 'grow', True)
                self._parseOption(entry, vol, 'fstype', 'fsType')
                self._parseOption(entry, vol, 'fsoptions', 'fsOptions')
                self._parseOption(entry, vol, 'name', 'name')
                self._parseOption(entry, vol, 'vgname', 'volGroup')

                vol['target'] = entry[1]

                self._vols.append(vol)
                continue

            # If we got here, there's something wrong
            raise ValueError("unknown descriptor %s" % entryType)


    def dump(self):
        return self._dumpDisk() + self._dumpPartition() + \
            self._dumpRaidDevice() + self._dumpVolumeGroup() + \
            self._dumpVolume()

    def getDisks(self):
        return self._disks

    def addDisk(self, device, initLabel=True, removeParts=None):
        """
        removeParts: None, LINUX, ALL

        device cciss/c0d0 , sda, hda, etc.
        """
        self.checkDevice(device)

        if not removeParts in [None, LINUX, ALL]:
            raise ValueError("removeParts needs to be None, LINUX or ALL")
        if device in self._disks:
            raise ValueError("device already defined")

        self._disks.append({'device': device,
            'initlabel': bool(initLabel),
            'removeParts': removeParts})

    def delDisk(self, diskId):
        # Check if it is used
        if self._disks[diskId]['device'] in [p['onDisk'] for p in self._parts]:
            raise ValueError("disk still in use")

        del self._disks[diskId]

    def _dumpDisk(self):
        res = ""
        for disk in self._disks:
            options = []
            if disk['initlabel']:
                options.append("--initlabel")
            if disk['removeParts'] == None:
                options.append("--none")
            if disk['removeParts'] == LINUX:
                options.append("--linux")
            if disk['removeParts'] == ALL:
                options.append("--all")
            res += "disk %s %s;" % (disk['device'], " ".join(options))
        return res

    def getPartitions(self):
        return self._parts

    def addPartition(self, target, size, maxSize=None, grow=False,
        formatPartition=True, boot=False, primary=False, fsType=None,
        fsOptions=None, encrypted=False, passphrase=None,
        onDisk=None):

        # Check target
        pt = re.compile(r"^(raid.[0-9][0-9]|swap|/.*|pv.[0-9][0-9])$")
        if not pt.match(target):
            raise ValueError("target %s is invalid" % target)
        if target in [part['target'] for part in self._parts]:
            raise ValueError("target already in use")

        # Check if disk exists
        if onDisk and not onDisk in [disk['device'] \
            for disk in self._disks + self._raids + self._volgroups]:
            raise ValueError("selected disk %s does not exist" % onDisk)

        # Size check
        if maxSize and maxSize < size:
            raise ValueError("maxSize must be greater than size")

        # Check for space
        info = self.getDeviceUsage()
        if info['disk'][onDisk]['size'] - info['disk'][onDisk]['usage'] < size:
            raise ValueError("not enough remaining space available")

        # Check fs options
        if fsType:
            self.checkFsType(fsType)
        if fsOptions:
            self.checkFsOptions(fsOptions)

        # Check for encryption
        if not self.supportEncryption and encrypted:
            raise ValueError("encryption not supported")

        # Assign values
        self._parts.append({
            "target": target,
            "size": size,
            "maxSize": None if not maxSize else maxSize,
            "grow": bool(grow),
            "format": bool(formatPartition),
            "primary": bool(primary),
            "bootable": bool(boot),
            "fsType": fsType,
            "fsOptions": fsOptions,
            "encrypted": bool(encrypted),
            "passphrase": passphrase,
            "onDisk": onDisk})

    def delPartition(self, partitionId):
        devs = []
        vgs = []
        if len(self._raids):
            for raid in self._raids:
                for dev in raid['devices']:
                    devs.append(dev)
        if len(self._volgroups):
            for vg in self._volgroups:
                for dev in vg['partitions']:
                    vgs.append(dev)

        if self._parts[partitionId]['target'] in vgs or self._parts[partitionId]['target'] in devs:
            raise ValueError("disk still in use")

        del self._parts[partitionId]

    def _dumpPartition(self):
        res = ""
        for part in self._parts:
            options = []
            options.append("--size %s" % part['size'])
            if part['maxSize']:
                options.append("--maxsize %s" % part['maxSize'])
            if part['grow']:
                options.append("--grow")
            if part['format']:
                options.append("--format")
            if part['bootable']:
                options.append("--bootable")
            if part['primary']:
                options.append("--asprimary")
            if part['fsType']:
                options.append("--fstype %s" % part['fsType'])
            if part['fsOptions']:
                options.append("--fsoptions \"%s\"" % part['fsOptions'])
            if part['encrypted']:
                options.append("--encrypted")
            if part['passphrase']:
                options.append("--passphrase \"%s\"" % part['passphrase'])
            if part['onDisk']:
                options.append("--ondisk %s" % part['onDisk'])
            res += "part %s %s;" % (part['target'], " ".join(options))
        return res

    def getRaidDevices(self):
        return self._raids

    def addRaidDevice(self, target, name, level="0", spares="0", fsType=None,
        fsOptions=None, formatDevice=True, useExisting=False, devices=None):

        # Check target
        pt = re.compile(r"^(swap|/[^/].*[^/]|pv.[0-9][0-9])$")
        if not pt.match(target):
            raise ValueError("target is invalid")
        if target in [part['target'] \
            for part in self._parts + self._raids + self._vols]:
            raise ValueError("target already in use")

        # Check level
        if not int(level) in [0, 1, 5]:
            raise ValueError("raid level unsupported")

        # Check raid devices
        if not devices:
            raise ValueError("need at least two devices")
        if len(devices) != len(list(set(devices))):
            raise ValueError("cannot use unique disks at once")
        pt = re.compile(r"^raid.[0-9][0-9]$")
        for device in devices:
            if not pt.match(device):
                raise ValueError("combined device %s is no raid device" % device)

            # Check if disk exists
            if not device in [part['target'] for part in self._parts]:
                raise ValueError("selected device %s does not exist" % device)

            # Check if already in use
            if self._raids and device in [dev for dev in
                [q['devices'] for q in self._raids]][0]:
                raise ValueError("selected device %s is already in use" % device)

        # Check level and device count
        if level == "0" and len(devices) < 1:
            raise ValueError("RAID 0 needs at least one device")
        if level == "1" and len(devices) < 2:
            raise ValueError("RAID 1 needs at least two devices")
        if level == "5" and len(devices) < 3:
            raise ValueError("RAID 5 needs at least three devices")

        # Check name
        pt = re.compile(r"^md[0-9]+$")
        if not pt.match(name):
            raise ValueError("name is invalid")
        if name in [raid['name'] for raid in self._raids]:
            raise ValueError("name already in use")

        # Check fs options
        if fsType:
            self.checkFsType(fsType)
        if fsOptions:
            self.checkFsOptions(fsOptions)

        # Assign values
        self._raids.append({
            "target": target,
            "name": name,
            "device": name,
            "level": level,
            "spares": None if not spares else spares,
            "useExisting": bool(useExisting),
            "format": bool(formatDevice),
            "fsType": fsType,
            "fsOptions": fsOptions,
            "devices": devices})

    def delRaidDevice(self, raidId):
        # Check for usage
        if self._volgroups and self._raids[raidId]['target'] in [part for part in [v['partitions'] \
            for v in self._volgroups]][0]:
            raise ValueError("raid device still in use")
        del self._raids[raidId]

    def _dumpRaidDevice(self):
        res = ""
        for raid in self._raids:
            options = []
            options.append("--level %s" % raid['level'])
            if raid['name']:
                options.append("--name %s" % raid['name'])
            if raid['spares']:
                options.append("--spares %s" % raid['spares'])
            if raid['format']:
                options.append("--format")
            if raid['useExisting']:
                options.append("--useexisting")
            res += "raid %s %s %s;" % (raid['target'], " ".join(options), " ".join(raid['devices']))
        return res

    def getVolumeGroups(self):
        return self._volgroups

    def addVolumeGroup(self, name, partitions, formatGroup=True,
        useExisting=False, peSize=None):

        # Check name
        pt = re.compile(r"^[a-zA-Z0-9_+-]+$")
        if not pt.match(name):
            raise ValueError("name is invalid")

        # Unique partition names?
        if len(partitions) != len(list(set(partitions))):
            raise ValueError("cannot use unique partitions at once")

        pt = re.compile(r"^pv.[0-9][0-9]$")
        for part in partitions:
            if not pt.match(part):
                raise ValueError("partition %s is no physical volume" % part)

            # Check if partition exists
            if not part in [disk['target'] for disk in self._parts + self._raids]:
                raise ValueError("selected partition %s does not exist" % part)

        # Assign values
        self._volgroups.append({
            "name": name,
            "device": name,
            "partitions": partitions,
            "format": bool(formatGroup),
            "useExisting": bool(useExisting),
            "peSize": None if not peSize else peSize})

    def delVolumeGroup(self, groupId):
        # Check for usage
        if self._volgroups[groupId]['name'] in [v['volGroup'] \
            for v in self._vols]:
            raise ValueError("volumegroup still in use")

        del self._volgroups[groupId]

    def _dumpVolumeGroup(self):
        res = ""
        for volume in self._volgroups:
            options = []
            if volume['peSize']:
                options.append("--pesize %s" % volume['pesize'])
            if volume['format']:
                options.append("--format")
            if volume['useExisting']:
                options.append("--useexisting")
            res += "volgroup %s %s %s;" % (volume['name'], \
                " ".join(options), " ".join(volume['partitions']))
        return res

    def getVolumes(self):
        return self._vols

    def addVolume(self, target, name, volGroup, size=None, maxSize=None,
        grow=False, formatVolume=True, useExisting=False,
        fsType=None, fsOptions=None):

        # Check target
        pt = re.compile(r"^(swap|/.*)$")
        if not pt.match(target):
            raise ValueError("target %s is invalid" % target)
        if target in [part['target'] for part in self._parts + self._raids + self._vols]:
            raise ValueError("target already in use")

        # Check volumegroup
        if not volGroup:
            raise ValueError("need a volume group")
        if not volGroup in [g['name'] for g in self._volgroups]:
            raise ValueError("selected volumegroup %s does not exist" % volGroup)

        # Check name
        pt = re.compile(r"^[a-zA-Z0-9_+-]+$")
        if not pt.match(name):
            raise ValueError("name is invalid")
        if name in [vol['name'] for vol in self._vols]:
            raise ValueError("name already in use")

        # Check for space
        info = self.getDeviceUsage()
        if info['vg'][volGroup]['size'] - info['vg'][volGroup]['usage'] < size:
            raise ValueError("not enough remaining space available")

        # Check fs options
        if fsType:
            self.checkFsType(fsType)
        if fsOptions:
            self.checkFsOptions(fsOptions)

        # Assign values
        self._vols.append({
            "target": target,
            "size": int(size),
            "maxSize": None if not maxSize else int(maxSize),
            "grow": bool(grow),
            "useExisting": bool(useExisting),
            "format": bool(formatVolume),
            "fsType": fsType,
            "fsOptions": fsOptions,
            "name": name,
            "volGroup": volGroup})

    def _dumpVolume(self):
        res = ""
        for volume in self._vols:
            options = []
            options.append("--size %s" % volume['size'])
            if volume['useExisting']:
                options.append("--useexisting")
            if volume['maxSize']:
                options.append("--maxsize %s" % volume['maxsize'])
            if volume['grow']:
                options.append("--grow")
            if volume['format']:
                options.append("--format")
            if volume['fsType']:
                options.append("--fstype %s" % volume['fsType'])
            if volume['fsOptions']:
                options.append("--fsoptions \"%s\"" % volume['fsOptions'])
            if volume['name']:
                options.append("--name %s" % volume['name'])
            if volume['volGroup']:
                options.append("--vgname %s" % volume['volGroup'])
            res += "logvol %s %s;" % (volume['target'], " ".join(options))
        return res

    def delVolume(self, volumeId):
        del self._vols[volumeId]

    def checkDevice(self, device):
        pt = re.compile(r"^(%s)$" % "|".join(self.supportedDeviceTypes))
        if not pt.match(device):
            raise ValueError("device %s is not supported" % device)

    def checkFsType(self, fsType):
        pt = re.compile(r"^(%s)$" % "|".join(self.supportedFsTypes))
        if not pt.match(fsType):
            raise ValueError("fsType %s is not supported" % fsType)

    def checkFsType(self, fsType):
        pt = re.compile(r"^(%s)$" % "|".join(self.supportedFsTypes))
        if not pt.match(fsType):
            raise ValueError("fsType %s is not supported" % fsType)

    def checkFsOptions(self, fsOptions):
        pt = re.compile(r"[a-zA-Z0-9=,.+_-]+")
        if not pt.match(fsOptions):
            raise ValueError("fsOptions %s are not valid" % fsOptions)

    def getFsTypes(self):
        return self.supportedFsTypes

    def getRaidLevels(self):
        return self.supportedRaidLevels

    def getUnassignedRaidPartitions(self):
        available = [part['target'] for part in self._parts if part['target'].startswith("raid.")]
        used = filter(lambda x: x.startswith('raid.'),
                list(itertools.chain(*[vg['partitions'] for vg in
                    self._volgroups] + [r['devices'] for r in self._raids])))
        return list(set(available) - set(used))

    def getUnassignedPhysicalVolumes(self):
        used = filter(lambda x: x.startswith('pv.'),
            list(itertools.chain(*[vg['partitions'] for vg in self._volgroups])))
        onpart = [part['target'] for part in self._parts if part['target'].startswith("pv.")]
        onraid = [part['target'] for part in self._raids if part['target'].startswith("pv.")]
        return list(set(onpart + onraid) - set(used))

    def getNextRaidName(self):
        current = [part['target'] for part in self._parts if part['target'].startswith("raid.")]
        return self.__next_value("raid.", current, fmt="%s%02d")

    def getNextRaidDevice(self):
        current = [raid['device'] for raid in self._raids if raid['device'].startswith("md")]
        return self.__next_value("md", current)

    def getNextPhysicalVolumeName(self):
        current = [raid['target'] for raid in self._raids if raid['target'].startswith("pv.")]
        current += [part['target'] for part in self._parts if part['target'].startswith("pv.")]
        return self.__next_value("pv.", current, fmt="%s%02d")

    def __next_value(self, prefix, current, start=0, limit=99, fmt="%s%d"):
        offset = len(prefix)
        current = map(lambda x: int(x[offset:]), current)
        current = filter(lambda x: x >= start and x <= limit, current)
        return fmt % (prefix,
            list(set(range(start, limit)) - set(current))[0])

    def getDeviceUsage(self):
        #TODO: take from inventory instead of hard coded values
        available_disks = {"sda": 20000, "sdb": 100000}

        # Calculate disks
        info = {'disk': {}, 'raid': {}, 'vg': {}, 'part': {}}
        for disk, size in available_disks.items():
            usage = sum([part['size'] for part in self._parts if part['onDisk'] == disk])
            info['disk'][disk] = {"size": size, "usage": usage}

        # Set up partitions for reference
        for part in self._parts:
            info['part'][part['target']] = {'size': part['size']}

        # Calculate RAIDs
        for raid in self._raids:
            size = 0
            if int(raid['level']) == 0:
                size = sum([info['part'][device]['size'] for device in raid['devices']])
            if int(raid['level']) == 1:
                size = min([info['part'][device]['size'] for device in raid['devices']])
            if int(raid['level']) == 5:
                size = min([info['part'][device]['size'] for device in raid['devices']])
                size = (len(raid['devices']) -1) * size

            info['raid'][raid['target']] = {"size": size}

        # Calculate volume groups
        for vg in self._volgroups:
            size = 0
            for part in vg['partitions']:
                if part in info['raid']:
                    size += info['raid'][part]['size']
                else:
                    size += info['part'][part]['size']

            usage = sum([vol['size'] for vol in self._vols if vol['volGroup'] ==
                vg['name']])

            info['vg'][vg['name']] = {"size": size, "usage": usage}

        return info


PluginRegistry.registerObject("libinst.diskdefinition", DiskDefinition)
