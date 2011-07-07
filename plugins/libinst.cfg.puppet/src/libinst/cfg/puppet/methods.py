# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: methods.py 1264 2010-10-22 12:28:49Z janw $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
import os.path
import pwd
import shutil
import pkg_resources
import StringIO
import ConfigParser
import ldap
from datetime import datetime
from libinst.methods import InstallMethod
from git import Repo
from git.cmd import Git, GitCommandError
from subprocess import Popen, PIPE
from threading import RLock
from types import StringTypes
from gosa.common.components.registry import PluginRegistry
from gosa.agent.ldap_utils import LDAPHandler
from nodes import PuppetNodeManager

# Global puppet lock
puppet_lock = RLock()

#TODO: Mirror handling and client handling -----------------------------------
#  -> hooks/post-commit
# git push device_uuid release:master
#-----------------------------------------------------------------------------


class PuppetInstallMethod(InstallMethod):

    _supportedTypes = ["deb"]
    _root = "PuppetRoot"

    def __init__(self, manager):
        super(PuppetInstallMethod, self).__init__(manager)

        # Use effective agent user's home directory
        self.__path = pwd.getpwuid(os.getuid()).pw_dir

        # Load install items
        for entry in pkg_resources.iter_entry_points("puppet.items"):
            module = entry.load()
            self.env.log.info("repository handler %s included" % module.__name__)
            self._supportedItems.update({
                module.__name__ : {
                        'name': module._name,
                        'description': module._description,
                        'container': module._container,
                        'options': module._options,
                        'module': module,
                    },
                })

        # Get a backend instance for that path
        self.__repo_path = os.path.join(self.__path, "repo")
        self.__work_path = os.path.join(self.__path, "work")

        # Purge path if wanted
        db_purge = self.env.config.getOption('db_purge', section = 'repository')
        if db_purge == "True":
            if os.path.exists(self.__repo_path):
                shutil.rmtree(self.__repo_path)
            if os.path.exists(self.__work_path):
                shutil.rmtree(self.__work_path)

        # Create path if it doesn't exist
        if not os.path.exists(self.__path):
            os.makedirs(self.__path, 0750)
        if not os.path.exists(self.__repo_path):
            os.makedirs(self.__repo_path, 0750)
        if not os.path.exists(self.__work_path):
            os.makedirs(self.__work_path, 0750)

        # Initialize git repository if not present
        if not os.path.exists(os.path.join(self.__repo_path, "config")):
            repo = Repo.create(self.__repo_path)
            assert repo.bare == True
            os.chmod(self.__repo_path, 0750)

            # Create master branch
            tmp_path = os.path.join(self.__work_path, "master")
            cmd = Git(self.__work_path)
            cmd.clone(self.__repo_path, "master")

            with open(os.path.join(tmp_path, "README"), "w") as f:
                f.write("This is an automatically managed GOsa puppet repository. Please do not modify.")

            logdir = self.env.config.getOption("report-dir", "puppet",
                "/var/log/puppet")
            with open(os.path.join(tmp_path, "puppet.conf"), "w") as f:
                f.write("""[main]
logdir=%s
vardir=/var/lib/puppet
ssldir=/var/lib/puppet/ssl
rundir=/var/run/puppet
factpath=$vardir/lib/facter
templatedir=$confdir/templates
report=true
reports=store_gosa
reportdir=$logdir
""" % logdir)

            # Add manifests and write initial size.pp
            os.mkdir(os.path.join(tmp_path, "manifests"))
            with open(os.path.join(tmp_path, "manifests", "site.pp"), "w") as f:
                f.write('import "manifests/nodes.pp"\n')

            # Add manifests and write initial size.pp
            with open(os.path.join(tmp_path, "manifests", "nodes.pp"), "w") as f:
                f.write('# Automatically managed by GOsa\n')

            cmd = Git(tmp_path)
            cmd.add("README")
            cmd.add("puppet.conf")
            cmd.add("manifests")
            cmd.commit(m="Initially created puppet master branch")
            cmd.push("origin", "master")
            shutil.rmtree(tmp_path)

        # Create SSH directory?
        self.ssh_path = os.path.join(self.__path, '.ssh')
        if not os.path.exists(self.ssh_path):
            os.makedirs(self.ssh_path)
            host = self.env.id
            user = pwd.getpwuid(os.getuid()).pw_name

            self.gen_ssh_key(os.path.join(self.ssh_path, 'id_dsa'),
                "%s@%s" % (user, host))

    @staticmethod
    def getInfo():
        return {
            "name": "Puppet",
            "title": "Puppet module repository",
            "description": "Description",
            }

    def getBaseDir(self, release=None):
        if release:
            release = release.replace("/", "@")
            return os.path.join(self.__work_path, release)
        else:
            return self.__work_path

    def createRelease(self, name, parent=None):
        super(PuppetInstallMethod, self).createRelease(name, parent)

        with puppet_lock:
            # Move to concrete directory name
            orig_name = name
            name = name.replace("/", "@")

            # Clone repository
            cmd = Git(self.__work_path)
            if parent:
                if isinstance(parent, StringTypes):
                    parent = parent.replace("/", "@")
                else:
                    parent = parent.name.replace("/", "@")
                self.env.log.debug("cloning new git branch '%s' from '%s'"
                        % (name, parent))
                cmd.clone(self.__repo_path, name, b=parent)
            else:
                self.env.log.debug("creating new git branch '%s'" % name)
                cmd.clone(self.__repo_path, name)

            # Switch branch, add information
            cmd = Git(os.path.join(self.__work_path, name))
            host = self.env.id
            cmd.config("--global", "user.name", "GOsa management agent on %s" % host)
            self.env.log.debug("switching to newly created branch")
            cmd.checkout(b=name)

            # Remove refs if there's no parent
            current_dir = os.path.join(self.__work_path, name)
            if not parent:
                self.env.log.debug("no parent set - removing refs")
                cmd.symbolic_ref("HEAD", "refs/heads/newbranch")
                os.remove(os.path.join(current_dir, ".git", "index"))
                files = os.listdir(current_dir)

                # Remove all but .git
                for f in files:
                    if f== ".git":
                        continue
                    if os.path.isdir(f):
                        shutil.rmtree(os.path.join(current_dir, f))
                    else:
                        os.unlink(os.path.join(current_dir, f))

            # Create release info file
            self.env.log.debug("writing release info file in %s" % current_dir)
            with open(os.path.join(current_dir, "release.info"), "w") as f:
                now = datetime.now()
                f.write("Release: %s\n" % orig_name)
                f.write("Date: %s\n" % now.strftime("%Y-%m-%d %H:%M:%S"))

            self.env.log.debug("comitting new release")
            cmd.add("release.info")
            cmd.commit(m="Created release information")

            # Push to origin
            self.env.log.debug("pushing change to central repository")
            cmd.push("origin", name)

        return True

    def removeRelease(self, name, recursive=False):
        super(PuppetInstallMethod, self).removeRelease(name, recursive)

        with puppet_lock:
            # Move to concrete directory name
            name = name.replace("/", "@")

            # Sort by length and remove relevant releases
            for fname in [f for f in sorted(
                os.listdir(self.__work_path), lambda a, b: cmp(b, a), len)
                if (recursive and f.startswith(name)) or (not recursive and f == name)]:

                current_dir = os.path.join(self.__work_path, fname)
                cmd = Git(current_dir)
                cmd.push("origin", ":" + fname)
                shutil.rmtree(current_dir)

        return True

    def renameRelease(self, name, new_name):
        super(PuppetInstallMethod, self).renameRelease(name, new_name)

        with puppet_lock:
            # Path conversation
            name = name.replace("/", "@")
            new_name = new_name.replace("/", "@")

            # Check if we've origins
            if len([f for f in os.listdir(self.__work_path) if f.startswith(name)]) > 1:
                raise ValueError("cannot rename release which contains childs")

            # Go for it
            current_dir = os.path.join(self.__work_path, name)
            cmd = Git(current_dir)
            cmd.branch("-m", name, new_name)
            cmd.push("origin", ":" + name)
            cmd.push("origin", new_name)
            os.rename(current_dir, os.path.join(self.__work_path, new_name))

        return True

    def getItemsAssignableElements(self, release, item):
        target_path, target_name = self.__get_target(release, item.path)
        module = self._supportedItems[item.item_type]['module'](target_path,
                target_name)
        return module.getAssignableElements()

    def getItem(self, release, path):
        super(PuppetInstallMethod, self).getItem(release, path)

        session = None

        item = self._get_item(release, path)
        if not item:
            return None

        try:
            session = self._manager.getSession()
            item = session.merge(item)

            target_path, target_name = self.__get_target(release, path)
            module = self._supportedItems[item.item_type]['module'](target_path, target_name)

        except:
            session.rollback()
            raise
        finally:
            session.close

        return module.get_options()

    def setItem(self, release, path, item_type, data, comment=None):
        result = super(PuppetInstallMethod, self).setItem(release, path, item_type, data)

        target_path, target_name = self.__get_target(release, path)
        module = self._supportedItems[item_type]['module'](target_path, target_name)

        for k, v in data.iteritems():
            module.set(k, v)

        # Let the module write the changes
        if not module.commit():
            return

        if not self.gitPush(self.getBaseDir(release)):
            return

        return result

    def removeItem(self, release, path, comment=None):
        result = None
        session = None
        try:
            session = self._manager.getSession()
            item = self._get_item(release, path)
            item = session.merge(item)
            target_path, target_name = self.__get_target(release, path)
            module = self._supportedItems[item.item_type]['module'](target_path, target_name)
            module.delete()

            # Commit changes
            if not comment:
                comment = "Change made with no comment"

            self.env.log.info("commiting changes for module %s" % target_name)
            cmd = Git(target_path)
            try:
                cmd.commit("-a", "-m", comment)
                cmd.push("origin")
            except GitCommandError as e:
                self.env.log.debug("no commit for %s: %s" % (target_name, str(e)))
            session.commit()
            result = True
        except:
            session.rollback()
            raise
        finally:
            session.close()
        result &= super(PuppetInstallMethod, self).removeItem(release, path)
        return result

    def gen_ssh_key(self, path, comment):
        for f in [path, path + ".pub"]:
            if os.path.exists(f):
                os.remove(f)

        args = ['ssh-keygen', '-t', 'dsa', '-N', '', '-C', comment, '-f', path]
        p = Popen(args, stdout=PIPE)
        p.communicate()[0]
        if p.returncode != 0:
            raise Exception("SSH key generation failed")

        return True

    def setConfigParameters(self, device_uuid, data, current_data=None):
        super(PuppetInstallMethod, self).setConfigParameters(device_uuid, data, current_data)
        if not self.addClient(device_uuid):
            cs = PluginRegistry.getInstance("ClientService")
            cs.systemSetStatus(device_uuid, "+P")

    def removeConfigParameters(self, device_uuid, current_data=None):
        super(PuppetInstallMethod, self).removeConfigParameters(device_uuid, current_data)
        self.removeClient(device_uuid)

    def get_ssh_pub_key(self, path):
        with open(path + ".pub") as f:
            content = f.readlines()

        return content[0].strip()

    def _git_get_config(self, cfg_file):
        data = ""

        for line in open(cfg_file, "r"):
            data += (line.lstrip())

            config = ConfigParser.ConfigParser()
            config.readfp(StringIO.StringIO(data))

            return config

    def addClient(self, device_uuid):
        cfg_file = os.path.join(self.__repo_path, "config")
        config = self._git_get_config(cfg_file)

        section = 'remote "%s"' % device_uuid
        if not config.has_section(section):
            cs = PluginRegistry.getInstance("ClientService")
            key = self._get_public_key()

            if not key[1] in [p["data"] for p in cs.clientDispatch(device_uuid, "puppetListKeys").values()]:
                cs.clientDispatch(device_uuid, "puppetAddKey", [key])

            # Load template and get the install method
            lh = LDAPHandler.get_instance()
            with lh.get_handle() as conn:
                #TODO: either replace with device or fix potential filter fsa
                res = conn.search_s(lh.get_base(), ldap.SCOPE_SUBTREE,
                    "(&(objectClass=configRecipe)(objectClass=installRecipe)(deviceUUID=%s))" % device_uuid,
                    ['cn', 'installRecipeDN', 'configVariable', 'configItem',
                    'installRelease'])

            # Bail out if not present
            if len(res) != 1:
                raise ValueError("unknown device %s" % device_uuid)

            data = res[0][1]

            # Load device variables
            variables = {}
            if 'configVariable' in data:
                for var in data['configVariable']:
                    key, value =  var.split('=', 1)
                    variables[key] = value

            # Get FQDN / Release
            fqdn = data['cn'][0].lower()
            release = "/".join(data['installRelease'][0].split("/")[1:])

            # Open nodes.pp and maintain it
            target_path, target_name = self.__get_target(release, "/")
            nodes_file = os.path.join(target_path, "manifests", "nodes.pp")

            #TODO: resolve recipe chain
            #data['installRecipe'][0]
            #->
            #node ldap-server {
            #  import "dns"
            #  include sudo
            #  include openldap
            #  include resolv
            #}
            inherit = None

            nm = PuppetNodeManager(nodes_file)
            nm.add(fqdn, variables, data['configItem'] if data['configItem'] else [], None)
            nm.write()
            del nm

            # Update git if needed
            self.gitPush(self.getBaseDir(release))

            # Add git configuration
            config.add_section(section)

            # Build push URL for client, it needs to be online
            try:
                url = cs.clientDispatch(device_uuid, "puppetGetPushPath")
                config.set(section, "url", url)
                with open(cfg_file, "w") as f:
                    config.write(f)
            except:
                return False

            # Reset "P" flag for client
            cs = PluginRegistry.getInstance("ClientService")
            cs.systemSetStatus(device_uuid, "-P")
            return True

    def removeClient(self, device_uuid):
        cfg_file = os.path.join(self.__repo_path, "config")
        config = self._git_get_config(cfg_file)

        section = 'remote "%s"' % device_uuid
        if config.has_section(section):
            # Remove ssh key
            #TODO: ...
            #puppetListKeys
            #puppetDelKey

            # Remove config sections
            config.remove_section(section)

            # Update value
            with open(cfg_file, "w") as f:
                config.write(f)

    def gitPush(self, path):
            # Announce changes to git
            cmd = Git(path)
            changed = False
            for line in cmd.status("--porcelain").splitlines():
                changed = True
                line = line.lstrip()
                self.env.log.info("staging changes for %s" % line.split(" ", 1)[1:])

                mode, file_path = line.split(" ", 1)
                file_path = os.path.join(*file_path.split("/")[0:])

                # Remove data?
                if mode == "D":
                    cmd.rm("-r", file_path)

                # Add data...
                else:
                    cmd.add(file_path)

            # No need to deal...
            if not changed:
                return False

            # Commit changes
            if not comment:
                comment = "Change made with no comment"

            self.env.log.info("committing changes for module %s" % target_name)
            cmd.commit("-m", comment)
            cmd.push("origin")

            return True

    def __get_target(self, release, path):
        """ Build target path for release """
        session = None
        path, target_name = path.rsplit("/", 1)
        try:
            session  = self._manager.getSession()
            path = self._get_relative_path(release, path)
            release = release.replace("/", "@")
            target_path = os.path.join(self.__work_path, release, path.strip("/"))
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        result = target_path, target_name
        return result

    def _get_public_key(self):
        default = os.path.join(os.path.expanduser('~'), ".ssh", "id_dsa.pub")

        try:
            with open(self.env.config.getOption("public_key", "puppet", default)) as f:
                content = f.read()
        except IOError:
                return ""

        return content.strip().split(" ")


    #TODO: Manage nodes.pp (!)
    def __update_nodes(self, device_uuid):
        nodes_file = os.path.join(self.__repo_path, "manifests", "nodes.pp")

        # Load all configRecipes and update the node hierarchy
        #TODO: cascading

        #node device-uuid {
        #    include configItem
        #}

        #node ldap-server {
        #  import "dns"
        #  include sudo
        #  include openldap
        #  include resolv
        #}
        #node 'dyn-10.muc.intranet.gonicus.de' inherits ldap-server {
        #  $test = "hallo"
        #}
