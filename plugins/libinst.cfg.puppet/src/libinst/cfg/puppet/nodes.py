# -*- coding: utf-8 -*-
import re
import os


class PuppetNodeManager(object):

    __node = re.compile("^node\s+['\"]?([^'\"\s]+)['\"]?(\s+inherits ['\"]?([^'\"]+)['\"]?)?\s*{$")
    __include = re.compile("^include\s+['\"]*([^'\"]+)['\"]*$")
    __var = re.compile("^\$([^\s=]+)\s*=\s*(['\"]?[^'\"]+['\"]?)$")

    def __init__(self, path):
        self.__path = path
        self.__nodes = {}

        trigger = False

        # Create file, if it does not exist yet
        if not os.path.exists(path):
            open(path, "a")

        for line in open(path, "r").readlines():
            line = line.strip()

            # Look for nodes
            if line.startswith("node "):
                name, dummy, inherit = self.__node.match(line).groups()
                if not name in self.__nodes:
                    self.__nodes[name] = {'var':{}, 'inherit':inherit, 'include':[]}

                trigger = True
                continue

            # Look at the stuff inside of the node definition
            if trigger:

                # ... trigger an store process if the node is ready
                if line.startswith("}"):
                    trigger = False
                    continue

                # ... save potential variables
                if line.startswith("$"):
                    key, value = self.__var.match(line).groups()
                    self.__nodes[name]['var'][key] = value

                # ... save potential includes
                if line.startswith("include"):
                    self.__nodes[name]['include'].append(self.__include.match(line).groups()[0])

    def add(self, name, variables={}, includes=[], inherit=None):
        self.__nodes[name] = {'var':variables, 'inherit':inherit, 'include':includes}

    def remove(self, name):
        del self.__nodes[name]

    def write(self):
        with open(self.__path, "w") as f:
            f.write(self.__repr__())

    def has(self, name):
        return name in self.__nodes

    def __repr__(self):
        res = ""

        for node, data in self.__nodes.items():
            res += "node '%s' %s{\n" % (node, "inherits " + data['inherit'] + " " if data['inherit'] else "")
            res += "\n".join(map(lambda x: "\tinclude %s" % x, data['include']))
            res += "\n"
            res += "\n".join(map(lambda x: "\t$%s = %s" % (x, data['var'][x]), data['var']))
            res += "\n}\n\n"
        return res.strip() + "\n"
