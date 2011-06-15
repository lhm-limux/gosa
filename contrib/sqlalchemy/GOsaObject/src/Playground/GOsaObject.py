from sqlalchemy.orm.interfaces import PropComparator
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import (MetaData, Table, Column, Integer, Unicode,
        ForeignKey, String, case,  cast, null, text,
        Boolean)
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.hybrid import hybrid_property

metadata = MetaData()




class VerticalProperty(object):
    """A key/value pair.

    This class models rows in the vertical table.
    """

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return '<%s %r=%r>' % (self.__class__.__name__, self.key, self.value)



class VerticalPropertyDictMixin(object):
    """Adds a dict-like access (obj[key]) to a mapped class.

    This is a mixin class.  It can be inherited from directly, or included
    with multiple inheritence.

    Classes using this mixin must define two class properties::

    _property_type:
      The mapped type of the vertical key/value pair instances.  Will be
      invoked with two positional arugments: key, value

    _property_mapping:
      A string, the name of the Python attribute holding a dict-based
      relationship of _property_type instances.

    Using the VerticalProperty class above as an example,::

      class MyObj(VerticalPropertyDictMixin):
          _property_type = VerticalProperty
          _property_mapping = 'props'

      mapper(MyObj, sometable, properties={
        'props': relationship(VerticalProperty,
                          collection_class=attribute_mapped_collection('key'))})

    Dict-like access to MyObj is proxied through to the 'props' relationship::

      myobj['key'] = 'value'
      # ...is shorthand for:
      myobj.props['key'] = VerticalProperty('key', 'value')

      myobj['key'] = 'updated value'
      # ...is shorthand for:
      myobj.props['key'].value = 'updated value'

      print myobj['key']
      # ...is shorthand for:
      print myobj.props['key'].value

    """
    _property_type = VerticalProperty
    _property_mapping = None

    __map = property(lambda self: getattr(self, self._property_mapping))

    def __getitem__(self, key):
        """
        Returns the value for the requested object property.
        """
        return self.__map[key].value

    def __setitem__(self, key, value):
        """
        Sets a new value for an object property.
        """
        property = self.__map.get(key, None)
        if property is None:
            self.__map[key] = self._property_type(key, value)
        else:
            property.value = value

    def __delitem__(self, key):
        """
        Deletes a property from this object
        """
        del self.__map[key]
        
    def __contains__(self, key):
        """
        An operator definition which allows to use the 'in'
        operator on objects.
        e.g.
           if 'name' in Object: 
        """
        return key in self.__map

    def keys(self):
        """
        Implements the dict like functionality for 'keys'
        """
        return self.__map.keys()

    def values(self):
        """
        Implements the dict like functionality for 'values'
        """
        return [prop.value for prop in self.__map.values()]

    def items(self):
        """
        Implements the dict like functionality for 'items'
        """
        return [(key, prop.value) for key, prop in self.__map.items()]

    def __iter__(self):
        """
        Implement iterator functionality
        """
        return iter(self.keys())


class GOsaProperty(object):
    """
    The GOsaProperty class handles object properties (GOsaObject['prop'])
    
    It consists of a 'key' and a 'value'.
    
        'key' is the equivalent of the GOsaProperty-table column 'key' due to
        sql-alchemy orm mappings.
        
        'value' is mapped depending on it type. Boolean value will be stored
        in boolean_value, strings in char_value, aso.
        
        This class takes care of this mapping transparently.
        
    The are two non-literal values, which are handled separately, due to the
    that they cannot be simply mapped, like flat flat values such as integers,
    string, aso.
    
    The first 'special' type is a link to another GOsaObject-instance. This link
    allows us to create graphs or connected objects. 
    
        e.g.
            user['address'] = GOsaObject('Address 1')
            user['address']['street'] = ... 
    
    The second 'special' type is a list, which enable us to store property
    collections in one single 'key'.
    
        e.g.
            user['notes'] = ['Einkaufen', 4711, GOsaObject('Something')]
    
    """

    # These are the two special attributes mentioned in the class description
    # above. 
    _childObject = None
    _listItems = None

    # The flat/literal value types we can handle.
    # If you want more values to be handled, then just extend the list and the 
    # GOsaProperty table definition in this file and drop the database.
    # SQL Alchemy will do the rest.
    type_map = {
        int: (u'integer', 'int_value'),
        unicode: (u'unicodechar', 'unicodechar_value'),
        str: (u'char', 'char_value'),
        bool: (u'boolean', 'boolean_value'),
        type(None): (None, None),
        }

    def __init__(self, key, value=None):
        """
        The constructor of this class, it takes a key and an optional value.
        """
        self.key = unicode(key)
        self.value = value
        
    def __repr__(self):
        return '<%s %r=%r>' % (self.__class__.__name__, self.key, self.value)

    @hybrid_property
    def value(self):
        """
        The getter method for dict like access from the GOsaObject instance.
        e.g.
            print House['walls']
        """

        # Return a directly linked object
        if self._childObject:
            return self._childObject
            
        # Return a list of objects
        if self._listItems:
            
            # Unpack the values from their GOsaProperty wrapping
            valueItems = map(lambda x: x.value , self._listItems)
            return valueItems
        
        # Return all other flat properties such as strings, boolean
        for discriminator, field in self.type_map.values():
            if self.type == discriminator:
                return getattr(self, field)
        
        # Return none if property wasn't found
        return None
    
    @value.setter
    def value(self, value):
        """
        The setter method for an GOsaObject property.
        Some value need special care, such as links to GOsaObject and lists, just 
        read the comments below for more details.
        """
        py_type = type(value)
        
        # Reset object links and lists
        self._childObject = None
        self._listItems = []
        
        # Save a direct link to another GOsaObject instance.
        # This enables object linking and graphs
        if isinstance(value, GOsaObject):
            self._childObject = value
            self.type = u'objectLink'
            return
        
        # Save a list properties
        if isinstance(value, list):
            
            # The list is emtpy
            if len(value) == 0:
                self._listItems = []
                return
                
            # Map values to GOsaProperty-instances, only GOsaProperty instances
            # can be handled by the orm mapper of sql-alchemy.
            # (Don't worry about orphaned-values, they will be cleaned up be
            #  by sql-alchemy automatically.)
            valueItems = map(lambda x: GOsaProperty(u'', x), value)
            self._listItems = valueItems
            self.type = u'itemList'     
            return

        # Save flat/literal values.
        # Check if the given object type is registered
        if py_type not in self.type_map:
            raise TypeError(py_type)

        # Walk through defined value types (self.type_map) to detect the 
        # correct column type for the given value.
        # Set all other columns to None, to avoid duplicated values in the 
        # GOsaProperty table.
        for field_type in self.type_map:
            discriminator, field = self.type_map[field_type]
            field_value = None
            if py_type == field_type:
                self.type = discriminator
                field_value = value
            if field is not None:
                setattr(self, field, field_value)

    @value.deleter
    def value(self):
        self._set_value(None)

    @value.comparator
    class value(PropComparator):
        """A comparator for .value, builds a polymorphic comparison via CASE.
            
            This allows us to query by object properties without specifying 
            which column type to query. 
            
            e.g. 
                session.query(GOsaObject).filter(GOsaObject.properties.any( \
                    GOsaProperty.value == u'Hickert'))
            
            instead of:
                session.query(GOsaObject).filter(GOsaObject.properties.any( \
                    GOsaProperty.unicodechar_value == u'Hickert'))

        """
        def __init__(self, cls):
            self.cls = cls

        def _case(self):
            whens = [(text("'%s'" % p[0]), getattr(self.cls, p[1]))
                     for p in self.cls.type_map.values()
                     if p[1] is not None]
            return case(whens, self.cls.type, null())
        
        def __eq__(self, other):
            return cast(self._case(), String) == cast(other, String)
        
        def __ne__(self, other):
            return cast(self._case(), String) != cast(other, String)



class GOsaObject(VerticalPropertyDictMixin):
    """
    The GOsaObject represents a node in our graph. 
    GOsaProperty are mapped into this class a dict-like way, by extending the
    VerticalPropertyDictMixin class from above.
    """
    _property_type = GOsaProperty
    _property_mapping = 'properties'
    
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)  


GOsaObjectTBL = Table('objects', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('name', Unicode(100)),
                    Column('type', Unicode(100))
                    )

GOsaPropertyTBL = Table('properties', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('key', Unicode(100)),
                    Column('type', Unicode(100)),
                    Column('char_value', String(100)),
                    Column('unicodechar_value', Unicode(100)),
                    Column('int_value', Integer()),
                    Column('boolean_value', Boolean()),
                    Column('parent_object', Integer, ForeignKey('objects.id')),
                    Column('links_to_object', Integer, ForeignKey('objects.id')),
                    Column('is_in_list', Integer, ForeignKey('properties.id'))
                    )


mapper(GOsaObject, GOsaObjectTBL, properties={
        'properties': relationship(
            GOsaProperty,
            primaryjoin=GOsaObjectTBL.c.id==GOsaPropertyTBL.c.parent_object,
            collection_class=attribute_mapped_collection('key')),
        }) 

mapper(GOsaProperty, GOsaPropertyTBL, properties={
        '_childObject': relationship(
            GOsaObject, 
            primaryjoin=GOsaObjectTBL.c.id==GOsaPropertyTBL.c.links_to_object),
        '_listItems': relationship(
            GOsaProperty,
            primaryjoin=GOsaPropertyTBL.c.is_in_list==GOsaPropertyTBL.c.id,
            cascade="all, delete, delete-orphan"
            )
        })


                