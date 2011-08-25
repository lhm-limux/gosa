# -*- coding: utf-8 -*-
from gosa.common.components import PluginRegistry
from libinst.interface import DiskDefinition


class DebianDiskDefinition(DiskDefinition):
    # Debian capabilities
    supportedFsTypes = ["reiserfs", "ext4", "ext3", "ext2", "swap", "vfat"]
    supportedDeviceTypes = ["hd[a-z]", "sd[a-z]", "cciss/c[0-9]d[0-9]"]
    supportEncryption = False

    def __init__(self, definition=None):
        super(DebianDiskDefinition, self).__init__(definition)

    def __str__(self):
        output = ""

        # Calculate possible partition numbers
        devices = {}
        for part in self._parts:
            if not part['onDisk'] in devices:
                devices[part['onDisk']] = []
            part['fullDevice'] = "/dev/%s%d" % (part['onDisk'], self.__getNextPartition(devices[part['onDisk']], part['primary']))

        # Gather used devices
        devices = set(["/dev/" + part['onDisk'] for part in self._parts])

        output += "d-i partman-auto/disk string %s\n" % ' '.join(devices)

        # Disk cleanup
        output += """d-i partman-auto/purge_lvm_from_device boolean true
d-i partman-lvm/purge_lvm_from_device boolean true
d-i partman-lvm/device_remove_lvm boolean true
d-i partman-md/device_remove_md boolean true
d-i partman-lvm/confirm boolean true
d-i partman/confirm boolean true
"""
        # Guess method
        if self._raids:
            output += "d-i partman-auto/method string raid\n"
        elif self._volgroups:
            output += "d-i partman-auto/method string lvm\n"
        else:
            output += "d-i partman-auto/method string regular\n"

        # Generate ordinary recipe
        part_def = "multiraid ::" if self._raids else ""

        # Do we create a RAID setup?
        if self._raids:
            # Merge partitioning information
            raid_map = {}
            raid_def = ""
            for raid in self._raids:
                raid_map[raid['name']] = [dev for dev in self._parts if dev['target'] in raid['devices']]

                raid_def += "%s %s %s %s %s . " % (
                    raid['level'],
                    len(raid_map[raid['name']]),
                    raid['spares'],
                    "lvm -" if raid['target'].startswith("pv") else raid['fsType'] + " " + raid['target'],
                    '#'.join([dev['fullDevice'] for dev in self._parts if dev['target'] in raid['devices']]))
            output += "d-i partman-auto-raid/recipe string " + raid_def.strip() + "\n"

        # Generate real partitioning information
        for part in self._parts:

            # Generate RAID partitions
            if part['target'].startswith("raid"):
                if not part['maxSize'] and part['grow']:
                    part['maxSize'] = "-1"
                part_def += "%(min_size)s %(ideal_size)s %(max_size)s raid " \
                    "$lvmignore{ } %(primary)s method{ raid } . " % {
                        'min_size': part['size'] / 2,
                        'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                        'ideal_size': part['size'],
                        'primary': "$primary{ }" if part['primary'] else ""}

            # Generate physical volumes
            if part['target'].startswith("pv"):

                # Lookup volume group
                for vg in [v for v in self._volgroups if part['target'] in v['partitions']]:
                    if not part['maxSize'] and part['grow']:
                        part['maxSize'] = "-1"

                    part_def += "%(min_size)s %(ideal_size)s %(max_size)s ext3 " \
                        "$defaultignore{ } %(primary)s method{ lvm } device{ %(device)s }"\
                        " vg_name{ %(name)s } . " % {
                            'min_size': part['size'] / 2,
                            'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                            'ideal_size': part['size'],
                            'primary': "$primary{ }" if part['primary'] else "",
                            'device': "/dev/" + part['onDisk'],
                            'name': vg['name']}

            # Generate swap volumes
            if part['target'].startswith("swap"):
                if not part['maxSize'] and part['grow']:
                    part['maxSize'] = "1000000000"
                part_def += "%(min_size)s %(ideal_size)s %(max_size)s linux-swap " \
                    "%(primary)s method{ swap } %(format)s . " % {
                        'min_size': part['size'] / 2,
                        'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                        'ideal_size': part['size'],
                         'primary': "$primary{ }" if part['primary'] else "",
                        'format': "format{ }" if part['format'] else ""}

            # Generate ordinary partitions
            if part['target'].startswith("/"):
                if not part['maxSize'] and part['grow']:
                    part['maxSize'] = "1000000000"
                part_def += "%(min_size)s %(ideal_size)s %(max_size)s %(fs_type)s " \
                    "%(primary)s use_filesystem{ } filesystem{ %(fs_type)s } " \
                    "mountpoint{ %(mountpoint)s } %(format)s . " % {
                        'min_size': part['size'] / 2,
                        'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                        'ideal_size': part['size'],
                        'mountpoint': part['target'],
                         'primary': "$primary{ }" if part['primary'] else "",
                        'fs_type': part['fsType'],
                        'format': "method{ format } format{ }" if part['format'] else ""}

        # LVM target partitions
        for part in self._vols:

            # Generate swap volumes
            if part['target'].startswith("swap"):
                if not part['maxSize'] and part['grow']:
                    part['maxSize'] = "1000000000"
                part_def += "%(min_size)s %(ideal_size)s %(max_size)s linux-swap " \
                    "$lvmok{ } in_vg{ %(volgroup)s } "\
                    " method{ swap } %(format)s . " % {
                        'min_size': part['size'] / 2,
                        'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                        'ideal_size': part['size'],
                        'volgroup': part['volGroup'],
                        'format': "format{ }" if part['format'] else ""}

            # Generate mounted volumes
            if part['target'].startswith("/"):
                if not part['maxSize'] and part['grow']:
                    part['maxSize'] = "1000000000"
                part_def += "%(min_size)s %(ideal_size)s %(max_size)s %(fs_type)s " \
                    "$lvmok{ } in_vg{ %(volgroup)s } "\
                    " use_filesystem{ } filesystem{ %(fs_type)s } mountpoint{ %(mountpoint)s } %(format)s  . " % {
                        'min_size': part['size'] / 2,
                        'max_size': part['maxSize'] if part['maxSize'] else part['size'],
                        'ideal_size': part['size'],
                        'mountpoint': part['target'],
                        'fs_type': part['fsType'],
                        'volgroup': part['volGroup'],
                        'format': "method{ format } format{ }" if part['format'] else ""}

        output += "d-i partman-auto/expert_recipe string %s" % ' '.join(part_def.split()) + "\n"

        # Finalize partition definition
        output += """d-i partman/confirm_write_new_label boolean true
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman-lvm/confirm_nooverwrite boolean true
d-i partman/confirm_nooverwrite boolean true
"""

        return output

    def __getNextPartition(self, partitions, primary=False):
        start = 1 if primary else 5
        end = 4 if primary else 15

        for nr in range(start, end + 1):
            if not nr in partitions:
                partitions.append(nr)
                return nr

        return None
