# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2011 GONICUS GmbH

 See LICENSE for more information about the licensing.
"""
import re
from urlparse import urlparse
from gosa.common.env import Environment
from gosa.common.components.registry import PluginRegistry
from libinst.methods import load_system
from libinst.methods import BaseInstallMethod
from libinst.disk import DiskDefinition, LINUX, ALL


class DebianPreseed(BaseInstallMethod):

    @staticmethod
    def getInfo():
        return {
            "name": "Preseed",
            "title": "Debian preseed installation method",
            "description": "Description",
            }

    def __init__(self):
        super(DebianPreseed, self).__init__()
        self.env = Environment.getInstance()
        self.path = self.env.config.getOption('path', 'libinst', default="/preseed")
        self.__http = PluginRegistry.getInstance('HTTPService')

        #TODO: add http service
        print "==================> SERVE!"

    def __attr_map(self, source, default=None, data=None):
        if not source in data:
            return default

        return data[source][0]

    def __load_release(self, data):
        release_path = data["installRelease"][0]

        #TODO: find configured mirror
        #      by inspecting installMirrorDN / installMirrorPoolDN
        #      for the moment, load it from the configuration file
        #      -> check if release_path debian/squeeze/1.0 is supported
        #         for the mirror
        #      -> if not available, automatically choose a mirror
        url = urlparse(self.env.config.getOption(
            'http_base_url', section='repository'))

        return {
            'mirror_protocol': url.scheme,
            'mirror_host': url.netloc,
            'mirror_path': url.path,
            'suite': "/".join(release_path.split("/")[1:]),
            }

    def __console_layout_code(self, data):
        return self.__attr_map("installSystemLocale", "en_US.UTF-8", data=data).split(".")[0]

    def __ntp(self, data):
        if not "installNTPServer" in data:
            return "d-i clock-setup/ntp boolean false"

        # Return space separated list of servers
        return "d-i clock-setup/ntp boolean true\n" + \
            "d-i clock-setup/ntp-server string " + \
            " ".join(data["installNTPServer"])

    def __kernel_package(self, data):
        if not "installKernelPackage" in data:
            return ""

        # Fill the kernel package
        return "d-i base-installer/kernel/image string " + data["installKernelPackage"][0]

    def __partition(self, data):
        if not "installPartitionTable" in data:
            return ""

        # Instanciate disk definition
        dd = DebianDiskDefinition(data['installPartitionTable'][0])
        return str(dd)

    def getBootConfiguration(self, device_uuid):
        super(DebianPreseed, self).getBootConfiguration(device_uuid)

        # Load device data
        data = load_system(device_uuid)

        # Attribute conversion
        mapped_data = {
            'installer_locale': self.__attr_map("installSystemLocale", "en_US.UTF-8", data=data),
            'installer_keymap': self.__attr_map("installKeyboardLayout", "us", data=data),
            'console_keymap': self.__attr_map("installKeyboardLayout", "us", data=data),
            'console_layout_code': self.__console_layout_code(data=data),
            'time_utc': "true" if self.__attr_map("installTimeUTC", "TRUE", data=data) == "TRUE" else "false",
            'time_zone': self.__attr_map("installTimezone", "GMT", data=data),
            'ntp': self.__ntp(data=data),
            'root_login_enabled': "true" if self.__attr_map("installRootEnabled", "FALSE", data=data) == "TRUE" else "false",
            'root_password_md5': self.__attr_map("installRootPasswordHash", "$1$2wd8zNj7$eWsmsB/lVdY/m4T8wi65W1", data=data),
            'kernel_package': self.__kernel_package(data=data),
            'partition': self.__partition(data=data),
            }
        mapped_data.update(self.__load_release(data=data))

        return data['templateData'].format(**mapped_data)

    def getBootParams(self, device_uuid):
        super(DebianPreseed, self).getBootParams(device_uuid)

        # Load device data
        data = load_system(device_uuid)

        arch = data["installArchitecture"][0]
        keymap = data["installKeyboardLayout"][0] \
            if "installKeyboardLayout" in data else "us"
        locale = data["installSystemLocale"][0] \
            if "installSystemLocale" in data else "en_US.UTF-8"

        url = "%s://%s:%s/%s/%s" % (
            self.__http.scheme,
            self.__http.host,
            self.__http.port,
            self.path.lstrip("/"),
            data['macAddress'][0] + ".cfg")

        hostname = data['cn'][0]
        #TODO: take a look at RFC 1279 before doing anything else
        domain = "please-fixme.org"

        params = [
            "vga=normal",
            "initrd=debian-installer/%s/initrd.gz" % arch,
            "netcfg/choose_interface=eth0",
            "locale=%s" % locale[:5],
            "debian-installer/country=%s" % locale[3:5],
            "debian-installer/language=%s" % locale[0:2],
            "debian-installer/keymap=%s" % keymap,
            "console-keymaps-at/keymap=%s" % keymap,
            "auto-install/enable=false",
            "preseed/url=%s" % url,
            "debian/priority=critical",
            "hostname=%s" % hostname,
            "domain=%s" % domain,
            "DEBCONF_DEBUG=5",
            ]

        return params


class DebianDiskDefinition(DiskDefinition):
    # Debian capabilities
    supportedFsTypes = ["reiserfs", "ext3", "ext2", "swap", "vfat"]
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
                member_devices = []
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
