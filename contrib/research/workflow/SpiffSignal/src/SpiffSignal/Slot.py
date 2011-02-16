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

class Slot(object):
    """
    Used internally to keep track of the subscribers for a signal.
    """
    def __init__(self):
        """
        Constructor.
        """
        self.subscribers = []

    def subscribe(self, user_func, *user_args):
        """
        Connect to the given function. When the signal is emitted using
        signal_emit(), the function is called with the arguments
        given in *args.

        @type  func: object
        @param func: The callback function.
        @type  *args: list
        @param *args: Arguments passed to the callback function.
        """
        self.subscribers.append((user_func, user_args))

    def is_subscribed(self, user_func):
        """
        Returns True if the given function is connected.

        @type  func: object
        @param func: The callback function.
        @rtype:  bool
        @return: Whether the signal is connected to the given function.
        """
        return user_func in [pair[0] for pair in self.subscribers]

    def unsubscribe(self, user_func):
        """
        Disconnects the from the given function.

        @type  func: object
        @param func: The callback function.
        """
        remove = []
        for i, pair in enumerate(self.subscribers):
            if pair[0] == user_func:
                remove.append(i)
        for i in remove:
            del self.subscribers[i]

    def unsubscribe_all(self):
        """
        Disconnects all functions.
        """
        self.subscribers = []

    def n_subscribers(self):
        """
        Returns the number of subscribers.

        @rtype:  int
        @return: The number of subscribers.
        """
        return len(self.subscribers)

    def signal_emit(self, *args, **kwargs):
        """
        Invokes the callbacks, passing the given arguments to them.

        @type  *args: list
        @param *args: Arguments passed to the callback function.
        @type  **kwargs: dict
        @param **kwargs: Keyword arguments passed to the callback function.
        """
        for func, user_args in self.subscribers:
            func(*args + user_args, **kwargs)
