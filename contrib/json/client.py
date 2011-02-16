#!/usr/bin/env python
# -*- coding: utf-8 -*-
from jsonrpc_proxy import JSONServiceProxy
from preseed import LINUX, ALL


def main():
    proxy = JSONServiceProxy('http://amqp.intranet.gonicus.de:8088')
    o = proxy.openObject("cn=Cajus Pollmeier,dc=gonicus,dc=de")

    o.addDisk('sda', ALL)
    o.addPartition("/boot", 250, {"onDisk":'sda', "boot":True, "fsType":"ext3",
        "primary":True})
    o.addPartition("pv.01", 40000, {"grow":True, "onDisk":'sda', "primary":True})
    o.addVolumeGroup("system", ["pv.01"])
    o.addVolume("/", "root", "system", {"size":4000, "fsType":"ext3"})
    o.addVolume("swap", "swap", "system", {"size":4000})
    o.addVolume("/usr", "usr", "system", {"size":5000, "fsType":"ext3"})
    o.addVolume("/srv", "srv", "system", {"size":10000, "grow":True, "fsType":"ext3"})
    o.addVolume("/var", "var", "system", {"size":4000, "fsType":"ext3"})
    o.addVolume("/home", "home", "system", {"size":10000, "fsType":"ext3"})

    print o.getDisks()
    print o.dump()


if __name__ == '__main__':
    main()
