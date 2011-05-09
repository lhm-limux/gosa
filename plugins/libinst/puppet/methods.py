# -*- coding: utf-8 -*-
"""
 This code is part of GOsa (http://www.gosa-project.org)
 Copyright (C) 2009, 2010 GONICUS GmbH

 ID: $$Id: methods.py 1264 2010-10-22 12:28:49Z janw $$

 This is the groupware interface class.

 See LICENSE for more information about the licensing.
"""
import os
import os.path
import re
import pwd
import shutil
import string
import pkg_resources
from datetime import datetime
from libinst.methods import InstallMethod
from git import Repo
from git.cmd import Git, GitCommandError
from subprocess import Popen, PIPE
from threading import RLock
from libinst.manage import RepositoryManager
from gosa.common.env import Environment
from types import StringTypes

# Global puppet lock
puppet_lock = RLock()

#TODO: Mirror handling and client handling -----------------------------------
#  -> config
# [remote "ws-muc-1"]
#         url = ssh://cajus@ws-muc-1/home/cajus/tmp/puppet
#
#  -> hooks/post-commit
# git push ws-muc-1 master
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

            cmd = Git(tmp_path)
            cmd.add("README")
            cmd.commit(m="Initially created master branch")
            cmd.push("origin", "master")
            shutil.rmtree(tmp_path)

        # Create SSH directory?
        ssh_path = os.path.join(self.__path, '.ssh')
        if not os.path.exists(ssh_path):
            os.makedirs(ssh_path)
            host = self.env.id
            user = pwd.getpwuid(os.getuid()).pw_name

            self.gen_ssh_key(os.path.join(ssh_path, 'id_dsa'),
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
        super(PuppetInstallMethod, self).setItem(release, path, item_type, data)

        target_path, target_name = self.__get_target(release, path)
        module = self._supportedItems[item_type]['module'](target_path, target_name)

        for k, v in data.iteritems():
            module.set(k, v)

        # Let the module write the changes
        if not module.commit():
            return

        # Add changes to git
        changed = False
        cmd = Git(self.getBaseDir(release))
        for line in cmd.status("--porcelain").splitlines():
            changed = True
            line = line.lstrip()
            self.env.log.info("staging changes for module %s" % line.split(" ", 1)[1:])

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
            return

        # Commit changes
        if not comment:
            comment = "Change made with no comment"

        self.env.log.info("committing changes for module %s" % target_name)
        cmd.commit("-m", comment)

    def removeItem(self, release, path, comment=None):
        item_type = self._get_item(release, path).item_type
        target_path, target_name = self.__get_target(release, path)
        module = self._supportedItems[item_type]['module'](target_path, target_name)
        module.delete()

        # Commit changes
        if not comment:
            comment = "Change made with no comment"

        self.env.log.info("commiting changes for module %s" % target_name)
        cmd = Git(target_path)
        try:
            cmd.commit("-a", "-m", comment)
        except GitCommandError as e:
            self.env.log.debug("no commit for %s: %s" % (target_name, str(e)))

        super(PuppetInstallMethod, self).removeItem(release, path)

    def gen_ssh_key(self, path, comment):
        for f in [path, path + ".pub"]:
            if os.path.exists(f):
                os.remove(f)

        args = ['ssh-keygen', '-t', 'dsa', '-N', '', '-C', comment, '-f', path]
        p = Popen(args, stdout=PIPE)
        stdout = p.communicate()[0]
        if p.returncode != 0:
            raise Exception("SSH key generation failed")

        return True

    def get_ssh_pub_key(self, path):
        with open(path + ".pub") as f:
            content = f.readlines()

        return content[0].strip()

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
