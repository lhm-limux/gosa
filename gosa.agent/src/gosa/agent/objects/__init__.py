# -*- coding: utf-8 -*-
"""
Object abstraction
==================

The object abstraction module allows to access managed information in an object oriented way.

You can get an object instance like this:

>>> from gosa.agent.objects import GOsaObjectFactory
>>> person = f.getObjectInstance('Person', "cn=Cajus Pollmeier,ou=people,ou=Technik,dc=gonicus,dc=de")

and then you can access, update and persist values like this:

>>> print person->sn
>>> print person->givenName
>>> person->sn = "New Surname"
>>> person->givenName = "Cajus"
>>> person->commit()
>>> person->close()

or call object methods:

>>> person->notify(u"Shutdown of your client", u"Please prepare yourselves for a system reboot!")

----

What properties are managed and how they are managed is defined in XML files.
Each of these XML files can contain one or more object defintions, you can find the them here ``./gosa.common/src/gosa/common/data/objects/``.

A detailed explanation of the XML defintion can be found here:
:ref:`title <intro>`
`GOsa Website <intro>`_
`GOsa Website <intro>`

An object definition consist of the following information:

 * Name
 * Description
 * A default backend which defines which storage backend is used to persist the data
 * A base RDN which specifies a storage container for these objects
 * Properties that are provided by this object
 * Methods that can be called on object instances


----


.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <Objects xmlns="http://www.gonicus.de/Objects">
        <Object>
            <Name>Person</Name>
            <Description>Person class</Description>
            <DefaultBackend>LDAP</DefaultBackend>
            <BaseRDN>ou=people</BaseRDN>

            <Methods>
                ...
            </Methods>
            <Attributes>
                ...
            </Attributes>
        </Object>
    </Objects>



#.. literalinclude:: ../../gosa.common/src/gosa/common/data/objects/person.xml
#   :language: xml



"""
__import__('pkg_resources').declare_namespace(__name__)
from gosa.agent.objects.factory import GOsaObjectFactory
