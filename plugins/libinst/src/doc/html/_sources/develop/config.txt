Config management modules
=========================

Config method
-------------

Modules get registered thru the setuptools ``[libinst.methods]`` section
and are available automatically.

-----

.. autoclass:: libinst.methods.InstallMethod
   :members:

Config items
------------

*InstallItem* is part of :class:`libinst.methods.InstallMethod` and is
used to describe a config management system. An implementator has to
define a structure of several items types that can be used by an
administrator to define the target system - independently of what
config mangement backend is used.

Lets discuss items by looking at the way `FAI <http://www.fai.org>`_ is
configured. They basically have this structure:

 * Class
    - Template
    - Script
    - Hook
    - Variables
    - Partitioning

So a *Class* can contains each of the subentries *Template*, *Script*,
*Hook*, *Variables* and *Partitioning*. Partitioning is not a
config management task, it's under the hood of
:class:`libinst.methods.BaseInstallMethod` - so, if someone want's
to implement FAI completely, there's the need to implement a base
install method for that, too.

Every other item type has to be implemented - and needs to be able
to determine if it's assigneable to a client::

    class FAIClass(InstallItem):
        _name = "FAIClass"
        _description = "A FAI class"
        _container = ["FAITemplate", "FAIScript", "FAIVariable", "FAIHook"]
        _prefix = "classes"
        _icon = "module"
        _options = {
                "name": {
                    "display": "Class name",
                    "description": "The name of the FAI class",
                    "type": "string",
                    "syntax": r"^[a-zA-Z0-9_+.-]+$",
                    "required": True,
                    "value": None,
                    "default": None,
                    },
		}
        ...

Defining all the required item types make the final FAI config
management work. The good thing about it: the potential GUI does
not need to know about FAI and it's items directly.

---------

An install item describes the smallest assigneable element of a
config management engine. It has a couple of control members:

============== =====================================================
Member         Description
============== =====================================================
_name          Item name
_description   Description
_container     List of modules that the current item can contain
_prefix        Filesystem (or what ever) prefix used for storage
_icon          Icon used to display this item
_options       List of properties this item provides
============== =====================================================

The options describe properties using key (= property name)/value
(=property description) pairs:

============== =====================================================
Key            Description
============== =====================================================
display        Display name
description    Description
type           Property type (string, integer, bool)
syntax         Optional regluar expression for additional validation
required       Flag to mark this property as mandatory
default        Default value if not explicitly set
============== =====================================================

---------

.. autoclass:: libinst.methods.InstallItem
   :members:
