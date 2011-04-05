# Copyright (C) 2007 Samuel Abels, http://debain.org
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from Slot import Slot

class Trackable(object):
    """
    Inherit from this class to add signal/event capability to a Python object.
    """
    def __init__(self):
        """
        Constructor.
        """
        self.slots = {}

    def signal_connect(self, name, func, *args):
        """
        Connects the signal with the given name to the given function.
        When the signal is emitted, the function is called with the arguments
        given in *args.

        @type  name: str
        @param name: The name of the signal.
        @type  func: object
        @param func: The callback function.
        @type  args: list
        @param args: Arguments passed to the callback function.
        """
        if not self.slots.has_key(name):
            self.slots[name] = Slot()
        self.slots[name].subscribe(func, *args)

    def signal_is_connected(self, name, func):
        """
        Returns True if the signal with the given name is connected to the
        given function.

        @type  name: str
        @param name: The name of the signal.
        @type  func: object
        @param func: The callback function.
        @rtype:  bool
        @return: Whether the signal is connected to the given function.
        """
        if not self.slots.has_key(name):
            return False
        return self.slots[name].is_subscribed(func)

    def signal_disconnect(self, name, func = None):
        """
        Disconnects the signal with the given name from the given function.

        @type  name: str
        @param name: The name of the signal.
        @type  func: object
        @param func: The callback function.
        """
        if not self.slots.has_key(name):
            return
        if func:
            self.slots[name].unsubscribe(func)
        else:
            self.slots[name].unsubscribe_all()

    def signal_disconnect_all(self):
        """
        Disconnects all connected functions from all signals.
        """
        for slot in self.slots.itervalues():
            slot.unsubscribe_all()
        self.slots = {}

    def signal_subscribers(self, name):
        """
        Returns the number of subscribers to the signal with the given name.

        @type  name: str
        @param name: The name of the signal.
        @rtype:  int
        @return: The number of subscribers.
        """
        if not self.slots.has_key(name):
            return 0
        return self.slots[name].n_subscribers()

    def signal_emit(self, name, *args, **kwargs):
        """
        Emits the signal with the given name, passing the given arguments
        to the callbacks.

        @type  name: str
        @param name: The name of the signal.
        @type  args: list
        @param args: Arguments passed to the callback function.
        @type  kwargs: dict
        @param kwargs: Keyword arguments passed to the callback function.
        """
        if not self.slots.has_key(name):
            return
        self.slots[name].signal_emit(*args, **kwargs)
