import time
import functools

class cache(object):

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
