#!/usr/bin/env python
import zope.event
from zope.interface import Interface, implements


class IObjectChanged(Interface):

    def reason():
        # Get change reason
        pass

    def uuid():
        # Get changed object uuid
        pass


class ObjectChanged(object):

    implements(IObjectChanged)

    def __init__(self, reason, uuid):
        self.__uuid = uuid
        self.__reason = reason

    def reason(self):
        return self.__reason

    def uuid(self):
        return self.__uuid


class ObjectEventHandler(object):

    def __call__(self, event):
        if IObjectChanged.providedBy(event):
            self.handleObjectChanged(event)

    def handleObjectChanged(self, event):
        print event.uuid()
        print event.reason()


zope.event.subscribers.append(ObjectEventHandler())

event = ObjectChanged('modify', 'c2df3c10-ef49-11e0-9225-5452005f1250')
zope.event.notify(event)
