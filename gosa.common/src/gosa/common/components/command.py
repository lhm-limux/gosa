"""
This code is part of GOsa (http://www.gosa-project.org)
Copyright (C) 2009, 2010 GONICUS GmbH

ID: $$Id: command.py 281 2010-07-02 07:43:23Z cajus $$

This is the zeroconf provider module.

See LICENSE for more information about the licensing.
"""
from inspect import getargspec

# Global command types
NORMAL = 1
FIRSTRESULT = 2
CUMULATIVE = 4


def Command(**d_kwargs):
    """
    This is the Command decorator. It adds properties based on its
    parameters to the function attributes.

    Example: @Command(needsQueue= False, type= NORMAL)

    @type needsQueue: bool
    @param needsQueue: indicates if the decorated function needs
                       a queue parameter

    @type type: int
    @param type: describes the function type

    Function types can be:

    * NORMAL (default)
      The decorated function will be called as if it is local. Which
      node will answer this request is not important.

    * FIRSTRESULT
      Some functionality may be distributed on several nodes with
      several information. FIRSTRESULT iterates thru all nodes which
      provide the decorated function and return on first success.

    * CUMULATIVE
      Some functionality may be distributed on several nodes with
      several information. CUMULATIVE iterates thru all nodes which
      provide the decorated function and returns the combined result.
    """
    def decorate(f):
        setattr(f, 'isCommand', True)
        for k in d_kwargs:
            setattr(f, k, d_kwargs[k])
        return f

    return decorate


def NamedArgs(d_collector=None, **d_kwargs):
    def decorate(f):
        d_kwds = {}
        d_args = getargspec(f).args
        d_index = d_args.index(d_collector)

        def new_f(*args, **kwargs):
            # Transfer
            if len(args) > d_index:
                for d_arg in [d for d in d_args if not d in kwargs and d in args[d_index]]:
                    kwargs.update({d_arg: args[d_index][d_arg]})

            f_result = f(*args, **kwargs)

            return f_result

        new_f.__doc__ = f.__doc__
        return new_f

    return decorate


class CommandInvalid(Exception):
    """ Exception which is raised when the command is not valid. """
    pass


class CommandNotAuthorized(Exception):
    """ Exception which is raised when the call was not authorized. """
    pass