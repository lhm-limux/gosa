import time
import functools

class cache(object):
    """
    Caching decorator basically taken from the
    `Python Wiki <http://wiki.python.org/moin/PythonDecoratorLibrary>`_.

    >>> @cache(ttl=60)
    >>> def fibonacci(n):
    ...    "Return the nth fibonacci number."
    ...    if n in (0, 1):
    ...       return n
    ...    return fibonacci(n-1) + fibonacci(n-2)
    >>>
    >>> fibonacci(12)

    ========= ============
    Parameter Description
    ========= ============
    ttl       time to cache results in seconds
    ========= ============
    """

    def __init__(self,  ttl=None):
        self.ttl = ttl
        self.cache = {}

    def __call__(self, func):

        def wrap(*args):
            now = time.time()

            try:
                rep = str(args)
                if rep in self.cache and (not self.ttl or (now -
                        self.cache[rep][1] < self.ttl)):
                    return self.cache[rep][0]
                else:
                    value = func(*args)
                    self.cache[rep] = (value, now)
                    return value

            except TypeError:
                return func(*args)

        return wrap

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)
