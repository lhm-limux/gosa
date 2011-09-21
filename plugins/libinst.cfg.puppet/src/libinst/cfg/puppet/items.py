# -*- coding: utf-8 -*-
import os
import re
import shutil
import logging
from libinst.interface import InstallItem
from gosa.common import Environment


class PuppetModule(InstallItem):
    _name = "Module"
    _description = "Puppet module"
    _container = ["PuppetManifest", "PuppetFile", "PuppetTemplate"]
    _prefix = "modules"
    _icon = "module"
    _options = {
            "name": {
                "display": "Module name",
                "description": "The name of the puppet module",
                "type": "string",
                "syntax": r"^[a-zA-Z0-9_+.-]+$",
                "required": True,
                "value": None,
                "default": None,
                },
            "description": {
                "display": "Module description",
                "description": "Text briefly describing the module contents",
                "type": "string",
                "required": False,
                "value": None,
                "default": None,
                },
            "version": {
                "display": "Module version",
                "description": "The version of the puppet module",
                "type": "string",
                "syntax": r"^[a-zA-Z0-9_+.-]+$",
                "required": True,
                "value": None,
                "default": None,
                },
            "dependency": {
                "display": "Module dependencies",
                "description": "Modules that are needed to be installed for this module",
                "type": "list",
                "syntax": r"^[a-zA-Z0-9_+\./-]+(\[[<=>]+[a-zA-Z0-9_+\.-]+\])?$",
                "required": False,
                "value": [],
                "default": [],
                },
        }

    def __init__(self, path, name):
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.__base = path
        self.__path = os.path.join(path, self._prefix, name)
        self.__name = name
        self.load()

    def load(self):
        self.set("name", self.__name)
        self.log.info("loading module %s" % self.__name)

        # Is new? Just live with the defaults...
        if not os.path.exists(self.__path):
            return True

        # Load module information into the data structure
        modulefile = os.path.join(self.__path, "Modulefile")
        if os.path.exists(modulefile):
            with open(modulefile, "r") as f:
                self.__load(f.readlines())
        else:
            raise Exception("'%s' contains no module file" % self.__path)

        # Mark it as unchanged
        self._changed = False

    def commit(self):
        super(PuppetModule, self).commit()

        # Check for a rename first
        if self.__name != self.get("name"):
            old = self.__path
            self.__path = os.path.join(self.__base, self._prefix,
                    self.get("name"))
            if os.path.exists(old):
                os.rename(old, self.__path)

        # Write data to filesystem structure
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        # Write back module file
        if self._changed:
            self.log.info("saving changes for module %s" % self.__name)

            modulefile = os.path.join(self.__path, "Modulefile")
            with open(modulefile, "w") as f:
                f.write("name '%s'\n" % self.get("name"))
                f.write("version '%s'\n" % self.get("version"))
                if self.get("description"):
                    f.write("\n")
                    f.write("description '%s'\n" % self.get("description"))

                reg = re.compile(r"^([^\[]+)(\[([<>=]+)?(.*)\])?$")
                deps = self.get("dependency")
                if len(deps):
                    f.write("\n")

                # Reorganize dependencies
                for dep in deps:
                    groups = reg.match(dep).groups()
                    if groups[1]:
                        if groups[2]:
                            version = groups[2] + " " + groups[3]
                        else:
                            version = groups[3]
                        f.write("dependency '%s', '%s'\n" % (groups[0], version))
                    else:
                        f.write("dependency '%s'\n" % groups[0])

        return self._changed

    def __load(self, lines):
        deps = []

        for line in [l.strip() for l in lines if l.strip()]:
            var, info = line.split(' ', 1)
            info = re.findall(r"'([^']+)'", info.strip())

            # Load plain entries
            for n in ["name", "version", "description"]:
                if var == n:
                    self.set(n, info[0])

            # Append dependencies
            if var == "dependency":
                if len(info) == 1:
                    deps.append(info[0])
                else:
                    deps.append("%s[%s]" % (info[0], info[1].replace(" ", "")))

        # Load dependencies
        self.set("dependency", deps)

    def delete(self):
        if os.path.exists(self.__path):
            try:
                shutil.rmtree(self.__path)
            except OSError:
                pass
            except:
                raise

    @staticmethod
    def scan(path):
        items = {}

        # Look into the given path/modules directory to check if there
        # are subdirectories. Assume that these are modules per convetion.
        for filename in os.listdir(u"" + os.path.join(path, PuppetModule._prefix)):
            abs_path = os.path.join(path, PuppetModule._prefix, filename)
            if os.path.isdir(abs_path):
                items[filename] = abs_path

        return items


class PuppetRoot(InstallItem):
    _name = "/"
    _description = "The root item"
    _container = ["PuppetModule"]
    _options = {}


class PuppetManifest(InstallItem):
    _name = "Manifest"
    _description = "Puppet manifest"
    _container = []
    _prefix = "manifests"
    _icon = "class"
    _options = {
            "name": {
                "display": "Manifest name",
                "description": "The name of the puppet manifest",
                "type": "string",
                "syntax": r"^[a-zA-Z0-9_+.-]+$",
                "required": True,
                "value": None,
                "default": None,
                },
            "data": {
                "display": "Manifest",
                "description": "Puppet manifest data",
                "type": "text",
                "required": True,
                "value": None,
                "default": None,
                },
        }

    def __init__(self, path, name):
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.__base = path
        self.__path = os.path.join(path, self._prefix)
        self.__name = name
        self.load()

    def load(self):
        self.set("name", self.__name)
        self.log.info("loading manifest %s" % self.__name)

        # Is new? Just live with the defaults...
        manifest_file = os.path.join(self.__path, self.__name + ".pp")
        if not os.path.exists(manifest_file):
            return True

        # Load data from manifest
        with open(manifest_file, "r") as f:
            self.set("data", f.read())

        # Mark it as unchanged
        self._changed = False

    def commit(self):
        super(PuppetManifest, self).commit()

        # Check for a rename first
        if self.__name != self.get("name"):
            old = os.path.join(self.__path, self.__name + ".pp")
            new = os.path.join(self.__path, self.get("name") + ".pp")
            self.__name = self.get("name")

            if os.path.exists(old):
                os.rename(old, new)

        # Write data to filesystem structure
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        # Write back module file
        if self._changed:
            self.log.info("saving changes for manifest %s" % self.__name)

            manifest_file = os.path.join(self.__path, self.__name + ".pp")
            with open(manifest_file, "w") as f:
                f.write(self.get("data"))

        return self._changed

    def delete(self):
        manifest_file = os.path.join(self.__path, self.__name + ".pp")
        os.remove(manifest_file)

    @staticmethod
    def manifest_validator(value):
        #TODO: validate stuff
        return True

    @staticmethod
    def scan(path):
        items = {}
        manifest_dir = os.path.join(path, PuppetManifest._prefix)

        # No manifests?
        if not os.path.exists(manifest_dir):
            return items

        # Look into the given path/manifests directory to check if there
        # are .pp files. Assume that these are manifests per convetion.
        for filename in os.listdir(u"" + manifest_dir):
            abs_path = os.path.join(manifest_dir, filename)
            if os.path.isfile(abs_path):
                # Remove trailing .pp
                filename = os.path.splitext(filename)[0]
                items[filename] = abs_path

        return items

    def getAssignableElements(self):
        class_re = re.compile(r"^\s*#\s*Class:\s*(.+)\s*$", re.IGNORECASE)
        parameter_re = re.compile(r"^\s*#\s*Parameters:\s*$", re.IGNORECASE)
        parameterv_re = re.compile(r"^\s*#\s*\$(.*):\s*$", re.IGNORECASE)
        breaker = re.compile(r"^\s*([^#]*|#\s*\w+:\s*)$", re.IGNORECASE)

        manifest_file = os.path.join(self.__path, self.__name + ".pp")

        if not os.path.exists(manifest_file):
            return {}

        with open(manifest_file, "r") as f:

            search_description = False
            search_parameters = False
            search_parameter_value = False

            classes = {}
            class_name = None
            description = ""
            parameters = {}
            parameter = ""

            # Parse line by line
            for line in f.readlines():
                line = line.strip()

                if breaker.match(line):
                    search_description = False
                    search_parameters = False
                    search_parameter_value = False

                # Look for new class line
                cm = class_re.match(line)
                if cm:

                    if class_name:
                        classes[class_name] = {
                                'description': description.strip(),
                                'parameter': parameters,
                                }
                        class_name = None
                        description = ""
                        parameters = {}
                        parameter = ""

                    class_name = cm.groups()[0]
                    search_description = True
                    continue

                # Look for parameters
                if parameter_re.match(line):
                    search_parameters = True
                    continue

                # Look for requires

                if search_parameters and line != "#":
                    para = parameterv_re.match(line)
                    if para:
                        parameter = para.groups()[0]
                        parameters[parameter] = ""
                        search_parameter_value = True
                        continue

                # Fill description
                if search_parameter_value:
                    if not parameters[parameter] and line == "#":
                        continue
                    parameters[parameter] += line.strip("#").strip() + "\n"

                # Fill description
                if search_description:
                    if not description and line == "#":
                        continue
                    description += line.strip("#").strip() + "\n"

            if not class_name in classes:
                classes[class_name] = {
                        'description': description.strip(),
                        'parameter': parameters,
                        }
                class_name = None
                description = ""
                parameters = {}
                parameter = ""

        return classes


class PuppetFile(InstallItem):
    _name = "File"
    _description = "Puppet file"
    _container = []
    _prefix = "files"
    _icon = "file"
    _options = {
            "name": {
                "display": "File name",
                "description": "The name of the puppet file",
                "type": "string",
                "syntax": r"^[a-zA-Z0-9_+.-]+$",
                "required": True,
                "value": None,
                "default": None,
                },
            "data": {
                "display": "File",
                "description": "Puppet file data",
                "type": "file",
                "required": True,
                "value": None,
                "default": None,
                },
        }

    def __init__(self, path, name):
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.__path = os.path.join(path, self._prefix)
        self.__name = name
        self.load()

    def load(self):
        self.set("name", self.__name)
        self.log.info("loading file %s" % self.__name)

        # Is new? Just live with the defaults...
        puppet_file = os.path.join(self.__path, self.__name)
        if not os.path.exists(puppet_file):
            return True

        # Load data from manifest
        with open(puppet_file, "r") as f:
            self.set("data", f.read())

        # Mark it as unchanged
        self._changed = False

    def commit(self):
        super(PuppetFile, self).commit()

        # Check for a rename first
        if self.__name != self.get("name"):
            old = os.path.join(self.__path, self.__name)
            new = os.path.join(self.__path, self.get("name"))
            self.__name = self.get("name")

            if os.path.exists(old):
                os.rename(old, new)

        # Write data to filesystem structure
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        # Write back module file
        if self._changed:
            self.log.info("saving changes for file %s" % self.__name)

            puppet_file = os.path.join(self.__path, self.__name)
            with open(puppet_file, "w") as f:
                f.write(self.get("data"))

        return self._changed

    def delete(self):
        puppet_file = os.path.join(self.__path, self.__name)
        os.remove(puppet_file)

    @staticmethod
    def scan(path):
        items = {}
        puppet_dir = os.path.join(path, PuppetFile._prefix)

        # No manifests?
        if not os.path.exists(puppet_dir):
            return items

        # Look into the given path/manifests directory to check if there
        # are .pp files. Assume that these are manifests per convetion.
        for filename in os.listdir(u"" + puppet_dir):
            abs_path = os.path.join(puppet_dir, filename)
            if os.path.isfile(abs_path):
                items[filename] = abs_path

        return items


class PuppetTemplate(InstallItem):
    _name = "Template"
    _description = "Puppet template"
    _container = []
    _prefix = "templates"
    _icon = "template"
    _options = {
            "name": {
                "display": "Template name",
                "description": "The name of the puppet template",
                "type": "string",
                "syntax": r"^[a-zA-Z0-9_+.-]+$",
                "required": True,
                "value": None,
                "default": None,
                },
            "data": {
                "display": "Template",
                "description": "Puppet template data",
                "type": "string",
                "required": True,
                "value": None,
                "default": None,
                },
        }

    def __init__(self, path, name):
        self.env = Environment.getInstance()
        self.log = logging.getLogger(__name__)
        self.__path = os.path.join(path, self._prefix)
        self.__name = name
        self.load()

    def load(self):
        self.set("name", self.__name)
        self.log.info("loading template %s" % self.__name)

        # Is new? Just live with the defaults...
        manifest_file = os.path.join(self.__path, self.__name + ".erb")
        if not os.path.exists(manifest_file):
            return True

        # Load data from manifest
        with open(manifest_file, "r") as f:
            self.set("data", f.read())

        # Mark it as unchanged
        self._changed = False

    def commit(self):
        super(PuppetTemplate, self).commit()

        # Check for a rename first
        if self.__name != self.get("name"):
            old = os.path.join(self.__path, self.__name + ".erb")
            new = os.path.join(self.__path, self.get("name") + ".erb")
            self.__name = self.get("name")

            if os.path.exists(old):
                os.rename(old, new)

        # Write data to filesystem structure
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        # Write back module file
        if self._changed:
            self.log.info("saving changes for template %s" % self.__name)

            manifest_file = os.path.join(self.__path, self.__name + ".erb")
            with open(manifest_file, "w") as f:
                f.write(self.get("data"))

        return self._changed

    def delete(self):
        manifest_file = os.path.join(self.__path, self.__name + ".erb")
        os.remove(manifest_file)

    @staticmethod
    def manifest_validator(value):
        #TODO: validate stuff
        return True

    @staticmethod
    def scan(path):
        items = {}
        manifest_dir = os.path.join(path, PuppetTemplate._prefix)

        # No manifests?
        if not os.path.exists(manifest_dir):
            return items

        # Look into the given path/manifests directory to check if there
        # are .erb files. Assume that these are manifests per convetion.
        for filename in os.listdir(u"" + manifest_dir):
            abs_path = os.path.join(manifest_dir, filename)
            if os.path.isfile(abs_path):
                # Remove trailing .erb
                filename = os.path.splitext(filename)[0]
                items[filename] = abs_path

        return items


# Add callbacks
PuppetManifest._options['data']['check'] = PuppetManifest.manifest_validator
