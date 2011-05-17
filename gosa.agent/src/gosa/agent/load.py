# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: load.py 605 2010-08-16 07:55:30Z cajus $$

 See LICENSE for more information about the licensing.
"""


class SystemLoad:
    """This class encapsulates methods to query the system load"""

    __timeList1 = [1, 1, 1, 1, 1, 1, 1, 1, 1]

    def getLoad(self):
        """
        Get current nodes CPU load.

        @rtype float
        @return load level
        """

        def getTimeList():
            """
            Fetches a list of time units the cpu has spent in various modes,
            details at http://www.linuxhowtos.org/System/procstat.htm
            """
            with file("/proc/stat", "r") as f:
                cpuStats = f.readline()
            columns = cpuStats.replace("cpu", "").split(" ")
            return map(int, filter(None, columns))

        timeList2 = getTimeList()
        dt = list([(t2 - t1) for t1, t2 in zip(self.__timeList1, timeList2)])

        idle_time = float(dt[3])
        total_time = sum(dt)
        load = 0.0
        if total_time != 0.0:
            load = 1 - (idle_time / total_time)
            # Set old time delta to current
            self.__timeList1 = timeList2

        return round(load, 2)
