Concept: Puppet Integration in GOsa-NG
======================================

This chapter explains the way `Puppet <http://www.puppetlabs.com/>`_ is integrated
in the libinst GOsa plugin.

Due to limitations of the original puppet master daemon (puppetmasterd) that ships with Puppet, GOsa uses
a simple GIT mechanism to push configuration data to its clients.

The limitations of the original puppetmasterd can be pointed out with two basic statements:

- puppetmasterd doesn't scale well
- we don't want another daemon running on GOsa-NG-Clients

Regarding the first statement there can be found a wealth of reports and considerations around scalability within puppet environments. There are different possiblities which all deal with the aim to integrate other web server in order to serve puppet's infrastructure. A direct consequence of this setup will be that a GOsa-NG-Server would have to deal with another service (other than GOsa-NG-daemon) and another technology/programming language (other than python/AMQP). 

The second statement is especially important regarding low performance and thin clients, but also deals with aspects of security and efficiency. Considering the abilities of the GOsa-NG-Client regarding communication and the possibilities of acquiring information about the client it is running on, there is simply no legitimation to start other daemons for achieving the same goal.

After all, the conclusion is that GOsa-NG will be integrated with puppet by running the so-called 'standalone' mode which is fully supported by the authors respectively puppetlabs.com .

-------------
Puppet Server
-------------

The default puppet setup deploys a classical client-server (2-tier) architecture in terms of organization, deployment and execution of puppet recipes (aka manifests aka configuration descriptions). 
Considering the aforementioned limitations of this implementation, a different approach was built that will fulfill the requirements in terms of scalability, flexibility and stability.

The server part of the puppet integration is represented by a simple GIT repository that will centrally hold and control all 
recipes of a GOsa-NG Instance. Administration of this repository can be done with git CLI or other git-tools which are 
widely available. Additionally, the GOsa Web Interface and Shell will be able to handle basic tasks such as committing 
new versions of recipes.

As GOsa-NG will not use the default communication between the puppetmaster daemon and the puppet client daemon, there 
has to be another way of delivering the recipes to the managed client. There are different possibilities regarding GIT, 
but GOsa-NG will rely on a simple git+ssh setup.

This setup will be built upon a central (Gosa-NG) Server which hosts the GIT repo as main source of the configuration data (recipes etc.). 
In addition to a basic GIT configuration, this central repo will be configured with the "Remote" feature of git.

By adding each client into the list of remote entries, distribution of the recipes to the gosa-ng-clients can be achieved
automatically using a push-mechanism. Using alias-names, it is possible to define groups of hosts which will be pushed, too.

An exemplary command would be

   ``# git push client master``

This command would result in a push of the recent source of the distinct client 'client' with the master-branch of the repository.

In case of mirroring of repositories, there are several possibilities, for example writing a post-commit hook to execute automated push actions for selected repositories or groups of repositories.

**TODO list** as of 2010/08/30: wie wird sowas angelegt, was macht die agent-Komponente, etc.

When creating branches of the repository, the server takes care of managing different releases by evaluating a release.info file which is residing in the root of each branch.

In case of manual interference within the repository, for example by editing and updating files in the repository directly via commandline, this file has to be adjusted accordingly. (using a tag mechanism as in SVN?)


-------------
Puppet Client
-------------

A registered client will receive a "bare" GIT-repository using the GOsa-NG-client communication. This bare repository is the basis for the push process originating from the puppet server.

By using a post-update hook inside the GIT repository, changes will be directly deployed to the default puppet directory /etc/puppet. The value of the directory is configurable within the GOsa-NG-Client. 

After copying the recipes to the puppet directory, the standalone binary will be called and therefore a puppet run will be executed.

For information and control purposes, puppet creates detailed logfiles in the YAML format. These are collected in a directory which is monitored by the GOsa-NG-Client. Using the UNIX-inotify mechanism, 
the client is able to collect and evaluate the log information and sends a corresponding event "puppet run successful/failed" to the GOsa-NG-server. 

The following list collects the system requirements for a GOsa-NG-Client which can use configuration management with puppet:

* sshd running
* puppet installed
* git installed
* gosa user with disabled password
* server must add ssh key auth via clientDispatch.puppetAddKey()

Handling of puppet recipes within the release management
--------------------------------------------------------

Implementation for InstallationItems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

     .. toctree::
        :glob:

        report=true
        reportdir=/var/log/puppet
        reports=store

