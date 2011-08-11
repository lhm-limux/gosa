# -*- coding: utf-8 -*-
"""
Object abstraction
==================

Basic usage
-----------

The object abstraction module allows to access managed-information in an object oriented way.

You can get an object instance like this:

>>> from gosa.agent.objects import GOsaObjectFactory
>>> person = f.getObjectInstance('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")

``(Instead of getting things by their 'dn', we will later use an UUID)``

and then you can access, update and persist values like this:

>>> print person->sn
>>> print person->givenName
>>> person->sn = "New Surname"
>>> person->givenName = "Cajus"
>>> person->commit()
>>> person->close()

or call object methods:

>>> person->notify(u"Shutdown of your client", u"Please prepare yourselves for a system reboot!")

.. warning::
    The following is not implemented yet!

or add and remove extension:

>>> person->addExtension('Mail')
>>> person->removeExtension('Posix')

.. warning::
    The following is not implemented yet!

Each object modification sends an event, with the related action and the objects uuid. These action
can then be caught later to perform different tasks, e.g. remove the mail-account from the server when
a Mail extension is removed.
 

How does it work - XML defintions for GOsa objects
--------------------------------------------------

What properties are managed and how they are managed is defined in a set of XML files.
Each of these XML files can contain one or more object defintions, you can find the them here ``./gosa.common/src/gosa/common/data/objects/``.

An object definition consist of the following information:

=============== ===========================
Name            Description
=============== ===========================
Name            The Name of the object
Description     A description
DefaultBackend  A default backend which defines which storage backend is used to persist the data
BaseRDN         A base RDN which specifies a storage container for these objects
Attributes      Properties that are provided by this object
Methods         Methods that can be called on object instances
Container       A list of potential sub-objects this object can contain
Extends         Another objects name that we can extend. E.g. Posix can extend a Person object
BaseObject      Defines this object as root object. E.g. Person is base object
=============== ===========================


XML defintion of GOsa-objects in detail
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
    We try to keep this documentation up to date, but at the moment the defintion
    changes fequently.


A minimum example
~~~~~~~~~~~~~~~~~

All starts with an ``<Object>`` which introduces a new GOsa-object, this
``<Object>`` tag must contain at least a ``<Name>``, a ``<Description>`` and a
``<DefaultBackend>`` tag. The name and the description are self-explaining.
The default-backend specifies which backend has to be used as default, for example
a LDAP or a MySQL backend. - There may be more depending on your setup.

Backends are storage points for GOsa-object information, they take care of caching, 
loading and saving of objects and their properties from different stores e.g. MySQL 
or LDAP.

Here is a minimum configuration for an GOsa-object. It does not have any
methods nor attributes:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        ...
        <Object>
            <Name>Dummy</Name>
            <Description>A dummy class</Description>
            <DefaultBackend>LDAP</DefaultBackend>
        </Object>
        ...
    </Objects>


Some optional properties added
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is a more complete example which include some optional values, but still
lacks attribute and method defintions: 

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        ...
        <Object>
            <Name>Person</Name>
            <Description>Person class</Description>
            <DefaultBackend>LDAP</DefaultBackend>

            <BaseRDN>ou=people</BaseRDN>
            <Container>
                <Type>Something</Type>
            </Container>
            <Extends>Base</Extends>
            <BaseObject>false</BaseObject>
        </Object>
        ...
    </Objects>

As you can see, four more tags were introduced here, a ``<BaseRDN>`` tag which specifies a
storage-container name for these kind of objects.

A ``<Container>`` tag which specifies for which objects we are a container.
For example an ``OrganizationalUnit`` can be a container for ``Person`` or ``Group`` objects.
In this example we could place ``Something`` objects under ``Person`` objects.

A ``Person`` object may have extensions like mail, posix, samba, ...  which can be added to or
removed from our object dynamically.
To be able to identify those addable extension we have the ``<Extends>`` tag, it specifies
which objects could be added to our object as extension.

The ``<BaseObject>`` tag, defines our object as root object, (if set to true) it cannot be attached
to some other objects, like describes above in the ``<Extends>`` tag.


With the above example we can now instantiate a ``Person`` object, it has no attributes
nor methods, but we could add a ``Posix`` and a ``Mail`` extension to it. And the backend
is told to store Person objects in 'ou=people'.

.. warning::
    The inheritance and extension handling is not implemented yet. But it will follow soon.
    In other words, these tags do not affect a GOsa-object right now: 
    ``BaseRDN``, ``Container``, ``BaseObject``, ``Extends``


Adding attributes and their in- and out-filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be able to store a users name or its postal address we need to define object-attributes.

Attributes can be access easily like this:

>>> print person->givenName

or can be set this way.

>>> person->postalAddress = "Herr Musterman\\n11111 Musterhausen\\nMusterstr. 55"

Here is a minimum example of an attribute:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        ...
        <Object>
            <Name>Person</Name>
            <DefaultBackend>LDAP</DefaultBackend>
            ...
            <Attributes>
                <Attribute>
                    <Name>sn</Name>
                    <Description>Surname</Description>
                    <Syntax>String</Syntax>
                </Attribute>
            </Attributes>
            ...
        </Object>
    </Objects>

The above definition creates an attribute named ``sn`` which is
stored in the LDAP backend. If you want to store this attribute in another Backend, then
you can specify it explicitly like this:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        ...
        <Object>
            <Name>Person</Name>
            <DefaultBackend>LDAP</DefaultBackend>
            ...
            <Attributes>
                <Attribute>
                    <Name>sn</Name>
                    <Description>Surname</Description>
                    <Backend>LDAP</Backend>
                    <Syntax>String</Syntax>
                </Attribute>
            </Attributes>
            ...
        </Object>
    </Objects>


Attribute definition can contain the follwoing tags, including optional:

=============== =========== ===========================
Name            Optional    Description
=============== =========== ===========================
Name            No          The attributes name
Description     No          A short description for the attribute
DependsOn       Yes         A list of attributes that depends on this attribute
Backend         Yes         The backend to store this attribute
Syntax          No          A simple string which defines the attributes syntax, e.g. String
Validators      Yes         A validation rule
InFilter        Yes         A filter which is used to read the attribute from the backend
OutFilter       Yes         A filter which is used to store the attribute in the backend
MultiValue      Yes         A boolean flag, which marks this value as multi value
Readonly        Yes         Marks the attribute as readonly
Mandatory       Yes         Marks the attribute as mandatory
=============== =========== ===========================

Here is an explanation of the simple properties above, the complex properties like ``Validators``,
``InFilter`` and ``OutFilter`` are described separately, later.

The tag ``<DependsOn>`` specifies a list of attributes that are related to the current attribute.
For example, the attribute 'cn' (common name) for a user is a combination of ``givenName`` and
``sn``, whenever you modify the users sn, you've to update the value of the ``cn`` attribute too.
If you now add ``cn`` to the ``<Depends>`` tag of the ``sn`` and ``givenName`` attributes, then
each modification of sn and givenName will mark the attribute cn as modified and thus forces it
to be saved again. (How sn and givenName are combined into the cn attribute will be described later
when the in- and outfilters are described).

With ``<Backend>`` you can specifiy another backend then defined in the ``<Object>s
<DefaultBackend>`` tag.

The ``<Syntax>`` specifies which syntax this attribute has, here is a list of all available values:

   * Boolean: bool
   * String: unicode
   * Integer: int
   * Timestamp: time.time
   * Date: datetime.date
   * Dictionary: dict
   * List: list
   * Binary

An attribute may have multiple values, for example you can have multiple phone numbers or mail addresses.
If you want an attribute to be multi value then just add the ``<MultiValue>`` tag and set it to true.

To create a readonly attribute add the tag ``<Readonly>`` and set it to true.

If the attribute is required to store the object then you should add the ``<Mandatory>`` flag and set it
to true.


Writing attribute validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use validators to check the value of an attribute.

Here is a simple example:

..code-block:: xml

        <Validators>
            <Condition>
                <Name>stringLength</Name>
                <Param>4</Param>
                <Param>20</Param>
            </Condition>
        </Validators>


This example uses the stringLength condition with a set of parameters to check the values length.
Right now there are a very limited set of conditions available - but there will be more.

You can also define more complex validators like this:





Creating in and out filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~


Introduction of methods
~~~~~~~~~~~~~~~~~~~~~~~

We can also define methods for GOsa-objects within the XML defintion, these methods can
then be called directly on an instance of these object:

>>> person->notify(u"Shutdown of your client", u"Please prepare yourselves for a system reboot!")

Here is the XML code for the above method call, all other object tags are removed for better reading:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        ...
        <Object>
            <Name>Person</Name>
            ...
            <Methods>
                <Method>
                    <Name>notify</Name>
                    <MethodParameters>
                        <MethodParameter>
                            <Name>notify_title</Name>
                            <Type>String</Type>
                            <Default>Notification</Default>
                        </MethodParameter>
                        <MethodParameter>
                            <Name>notify_message</Name>
                            <Type>String</Type>
                            <Required>true</Required>
                        </MethodParameter>
                    </MethodParameters>
                    <Command>notifyUser</Command>
                    <CommandParameters>
                        <CommandParameter>
                            <Value>%(uid)s</Value>
                        </CommandParameter>
                        <CommandParameter>
                            <Value>Der angegebene Titel war: %(notify_title)s</Value>
                        </CommandParameter>
                        <CommandParameter>
                            <Value>%(notify_message)s</Value>
                        </CommandParameter>
                    </CommandParameters>
                </Method>
            </Methods>
            ...
        </Object>
    </Objects>

Methods are introduced by a ``<Method>`` tag and are grouped within the ``<Methods>`` tag.
You can have multiple methods if you want.

Methods consist of four tags:

    * The ``<Name>`` tag which specifies the name of the method.
    * A ``<MethodParameters>`` tag, which contains a list of parameters to this method.
    * A ``<Command>`` tag, which represents to GOsa-agent command we want to call.
    * The ``<CommandParameters>`` tag, defines a list parameters we want to pass to the
      GOsa-agent command call.

The above defintion creates a method named notify which looks like this:

>>> def notify(notify_message, notify_title = u"Notification"):

If you call this method like this:

>>> person->notifyUser("Warning", "Restart imminent!")

it will invoke a GOsa-agent command named notifyUser with this parameters:

>>> notifyUser(u"user1", u"Der angegebene Titel war: Warning", u"Restart imminent!")

As you can see, you cannot freely create whatever method you want, you can just call
existing GOsa-agent commands and adjust their arguments.

You can use placeholders using ``%(property_name)s``, to dynamically fill in
command parameters, like done for the first ``<CommandParameter>``.

.. code-block:: xml

    <CommandParameter>
        <Value>%(uid)s</Value>
    </CommandParameter>

or you can use it to refer to the method-parameters like this:

.. code-block:: xml

    <CommandParameter>
        <Value>Placeholder: %(notify_message)s</Value>
    </CommandParameter>

You can use all the attribute names you have defined and additionally all the
parameters of the method as placeholders.


"""
__import__('pkg_resources').declare_namespace(__name__)
from gosa.agent.objects.factory import GOsaObjectFactory
