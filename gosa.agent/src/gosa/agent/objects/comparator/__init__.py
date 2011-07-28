# -*- coding: utf-8 -*-
__import__('pkg_resources').declare_namespace(__name__)
import pkg_resources


def get_comparator(name):
    for entry in pkg_resources.iter_entry_points("gosa.object.comparator"):

        module = entry.load()
        if module.__name__ == name:
            return module

    raise KeyError("no comparator instance for '%s' found" % name)


class ElementComparator(object):

    def __init(self, obj):
        pass

    def process(self, *args, **kwargs):
        raise NotImplementedError("not implemented")
