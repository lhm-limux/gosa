Introduction
============

Quickstart
----------

This document contains information on *how to get started* with
the current gosa 3.0 alpha. It does not care about SSL or other
security related issues around qpid.

It works starting with squeeze or later.

.. warning::

    Lenny does not work, so you just don't have to try...

Depending on which parts of gosa-ng you want to deploy, there are
different prequisites to fulfill. Please read the relevant sections.


Common setup
^^^^^^^^^^^^

System prequisites
""""""""""""""""""

To run the services in the designed way later on, you need a special user
and a couple of directories::

    $ sudo adduser --system --group gosa --home=/var/lib/gosa

If you're going to run the service in daemon mode, please take care that
there's a */var/run/gosa* for placing the PID files.


Python prequisites
""""""""""""""""""

While we try to keep everything inside a virtual python environment for
development, some of the python modules need compilation - which rises the
number of required packages drastically. For the time beeing, please install
the following packages in your system::

  $ sudo apt-get install python2.6-dev python-dumbnet python-avahi python-virtualenv \
         libavahi-compat-libdnssd-dev python-openssl python-dbus libssl-dev python-gtk2 \
         python-lxml python-libxml2 python-dmidecode python-ldap python-nose \
         python-kid python-coverage python-dateutil python-smbpasswd python-netifaces

.. note::
      On MS Windows systems, only the client is supposed to work. Please install the
      ywin32 package: http://sourceforge.net/projects/pywin32/


Setup a virtual environment for playing with GOsa 3.0 alpha
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

As a non-root user, initialize the virtual environment::

  $ virtualenv --setuptools --python=python2.6  gosa-ng
  $ cd gosa-ng
  $ source bin/activate


Obtaining the source
""""""""""""""""""""

For now, please use the tar or git::

   $ cd 'the place where you created the gosa-ng virtualenv'
   $ git clone git://oss.gonicus.de/git/gosa.git src

This will place all relevant files inside the 'src' directory.

.. warning::
      The "source bin/activate" has to be done every time you work in or with the
      virtual environment. Stuff will fail if you don't do this. If you're asked for
      sudo/root, you're doing something wrong.


The gosa-ng agent
^^^^^^^^^^^^^^^^^

To run the agent, you most likely need a working AMQP broker and
a working LDAP setup.


Prequisites
"""""""""""

We use qpidc as the AMQP broker. Other implementations like rabbitmq,
etc. are not supported. They lack some functionality we're making use
of.


Adding the AMQP repository
""""""""""""""""""""""""""

In Debian, the simpliest way to get qpid running would be the use
of an existing repository. Include it in your configuration like this::

  # wget -O - http://apt.naasa.net/archive.key | apt-key add -
  # [ -d /etc/apt/sources.d ] || mkdir /etc/apt/sources.d
  # echo "deb http://apt.naasa.net/debian/ lenny main" > /etc/apt/sources.d/qpid.list
  # apt-get update


Install qpid broker and clients
"""""""""""""""""""""""""""""""

::

  # apt-get install qpid-broker qpid-client qpid-utils qpid-specs

Add a user for playing with the current development snapshot::

  # saslpasswd2 -f /var/lib/qpidd/qpidd.sasldb -u QPID admin

Maybe set the access policy for the admin. Not directly needed for non-production,
but a definitive must on ordinary systems::

  # vi /etc/qpid/qpidd.policy
  |# Admin is allowed to do everything
  |acl allow admin all
  |
  |# Deny everything else by default
  |acl allow all deny
  |:wq

Check if it works::

  # qpid-config -a admin/secret@hostname queues

Now the broker aka bus is up and running on the host.


For production use, you should enable SSL for the broker and for GOsa core. Generating
the certificates is shown here:

http://rajith.2rlabs.com/2010/03/01/apache-qpid-securing-connections-with-ssl/


Install LDAP service
""""""""""""""""""""

#TODO


AMQP LDAP-Authentication
""""""""""""""""""""""""

/etc/default/saslauthd::

  #
  # Settings for saslauthd daemon
  # Please read /usr/share/doc/sasl2-bin/README.Debian for details.
  #
  
  # Should saslauthd run automatically on startup? (default: no)
  START=yes
  
  # Description of this saslauthd instance. Recommended.
  # (suggestion: SASL Authentication Daemon)
  DESC="SASL Authentication Daemon"
  
  # Short name of this saslauthd instance. Strongly recommended.
  # (suggestion: saslauthd)
  NAME="saslauthd"
  
  # Which authentication mechanisms should saslauthd use? (default: pam)
  #
  # Available options in this Debian package:
  # getpwent  -- use the getpwent() library function
  # kerberos5 -- use Kerberos 5
  # pam       -- use PAM
  # rimap     -- use a remote IMAP server
  # shadow    -- use the local shadow password file
  # sasldb    -- use the local sasldb database file
  # ldap      -- use LDAP (configuration is in /etc/saslauthd.conf)
  #
  # Only one option may be used at a time. See the saslauthd man page
  # for more information.
  #
  # Example: MECHANISMS="pam"
  MECHANISMS="ldap"
  
  # Additional options for this mechanism. (default: none)
  # See the saslauthd man page for information about mech-specific options.
  MECH_OPTIONS=""
  
  # How many saslauthd processes should we run? (default: 5)
  # A value of 0 will fork a new process for each connection.
  THREADS=5
  
  # Other options (default: -c -m /var/run/saslauthd)
  # Note: You MUST specify the -m option or saslauthd won't run!
  #
  # WARNING: DO NOT SPECIFY THE -d OPTION.
  # The -d option will cause saslauthd to run in the foreground instead of as
  # a daemon. This will PREVENT YOUR SYSTEM FROM BOOTING PROPERLY. If you wish
  # to run saslauthd in debug mode, please run it by hand to be safe.
  #
  # See /usr/share/doc/sasl2-bin/README.Debian for Debian-specific information.
  # See the saslauthd man page and the output of 'saslauthd -h' for general
  # information about these options.
  #
  # Example for postfix users: "-c -m /var/spool/postfix/var/run/saslauthd"
  OPTIONS="-c -m /var/run/saslauthd"


/etc/saslauthd.conf::

  ldap_servers: ldap://ldap.your.domain
  ldap_search_base: dc=example,dc=com
  ldap_filter: (|(&(objectClass=gosaAccount)(uid=%U))(&(objectClass=registeredDevice)(deviceUUID=%U)))
  ldap_scope: sub
  ldap_size_limit: 0
  ldap_time_limit: 15
  ldap_timeout: 15
  ldap_version: 3
  ldap_debug: 255


Test::

  # /etc/init.d/saslauthd restart
  # testsaslauthd -u admin -p secret -r QPID


/etc/qpid/sasl/qpidd.conf::

  pwcheck_method: saslauthd
  mech_list: PLAIN LOGIN

Start up service::

  # adduser qpidd sasl
  # /etc/init.d/qpid-broker restart


Prepare DNS-Zone for zeroconf
"""""""""""""""""""""""""""""

Zeroconf setup::

  ; Zeroconf base setup
  b._dns-sd._udp  IN PTR @   ;  b = browse domain
  lb._dns-sd._udp IN PTR @   ;  lb = legacy browse domain
  r._dns-sd._udp  IN PTR @   ;  r = registration domain

  ; Zeroconf gosa-ng records
  _gosa._tcp  PTR GOsa\ NG\ Service._gosa._tcp
  GOsa\ NG\ Service._gosa._tcp     SRV 0 0 5671 amqp.example.org.
                                 TXT amqps://amqp.example.org:5671/org.gosa

You can test your setup with::

  # avahi-browse -D
  -> this should list your domain
  # avahi-browse -r example.org _gosa._tcp
  -> this should list your services


Deploy a development agent
""""""""""""""""""""""""""

To deploy the agent, please run these commands inside the activated
virtual environment::

  $ ./setup_common.py develop
  $ ./setup_agent.py develop

Alternatively you can build the complete package using::

  $ ./setup.py develop


Starting the service
""""""""""""""""""""

Take a look at the agent.conf present in the src/gosa/agent/data directory and adapt it
to your needs. Fire up the daemon in foreground mode::

  $ gosa-agent -f --config=src/gosa/agent/data/agent.conf

If you want to run the agent in a more productive manner, you can use the
daemon mode and start it as root. It will then fork to the configured user
and run as a daemon.

.. warning::
    Make sure, you've entered the virtual environment using "source bin/activate"
    from inside the gosa-ng directory.


The gosa-ng shell
^^^^^^^^^^^^^^^^^

Installing
""""""""""

To deploy the shell, use::

  $ ./setup_common.py develop
  $ ./setup_shell.py develop

inside your activated virtual env. You can skip this if you ran ./setup.py for
a complete deployment.


First contact
^^^^^^^^^^^^^

The gosa-shell will use zeroconf/DNS to find relevant connection methods. Alternatively
you can specify the connection URL to skip zeroconf/DNS.

Start the shell and send a command::

  $ gosa-shell
  (authenticate as the admin user you've created in qpid's SASL DB)
  >>> gosa.help()
  >>> gosa.mksmbhash("secret")
  >>> <Strg+D>

The shell did not get priorized work in the moment, so the gosa.help() output is
neither sorted, nor grouped by plugins. Much space for improvements.

If you tend to use a connection URL directly, use::

  $ gosa-shell http[s]://amqp.example.com:8080/rpc

for HTTP based sessions or ::

  $ gosa-shell amqp[s]://amqp.example.com/org.gosa

for AMQP based sessions.


The gosa-ng client
^^^^^^^^^^^^^^^^^^

A gosa-ng client is a device instance that has been joined into the gosa network.
Every client can incorporate functionality into the network - or can just be
a managed client.


Installing
""""""""""

To deploy the client components, use::

  $ ./setup_common.py develop
  $ ./setup_client.py develop
  $ ./setup_dbus.py develop

inside your activated virtual env. You can skip this if you ran ./setup.py for
a complete deployment.


Joining the party
"""""""""""""""""

A client needs to authenticate to the gosa-ng bus. In order to create the required
credentials for that, you've to "announce" or "join" the client to the system.

To do that, run ::

  $ sudo -s
  # cd 'wherever your gosa-ng virtual environment is'
  # source/bin activate
  # gosa-join

on the client you're going to join. In the development case, this may be the
same machine which runs the agent.


Running the root component
""""""""""""""""""""""""""

Some functionality may need root permission, while we don't want to run the complete
client as root. The gosa-dbus component is used to run dedicated tasks as root. It
can be extended by simple plugins and registers the resulting methods in the dbus
interface.

To use the dbus-component, you've to allow the gosa system user (or whatever user
the gosa-client is running later on) to use certain dbus services. Copy and eventually
adapt the file src/contrib/dbus/com.gonicus.gosa.conf to /etc/dbus/service.d and
reload your dbus service. ::

  $ sudo service dbus reload

To start the dbus component, activate the python virtual environment as root and run
the gosa-dbus component in daemon or foreground mode::

  $ sudo -s
  # cd 'wherever your gosa-ng virtual environment is'
  # source/bin activate
  # gosa-dbus -f


Running the client
""""""""""""""""""

To run the client, you should put your development user into the gosa group - to
be able to use the dbus features::

  $ sudo adduser $USER gosa

You might need to re-login to make the changes happen. After that, start the gosa-ng
client inside the activated virtual environment::

  $ gosa-client -f


Concepts
--------

**TODO**: graphics, text, etc.
