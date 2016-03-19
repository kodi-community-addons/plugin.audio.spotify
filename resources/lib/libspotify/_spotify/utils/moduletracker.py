'''
Created on 09/05/2012

@author: mikel
'''
import weakref


_tracked_modules = {}


def _untrack_module(ref):
    del _tracked_modules[id(ref)]


def track_module(item):
    ref = weakref.ref(item, _untrack_module)
    _tracked_modules[id(ref)] = ref


def count_tracked_modules():
    return len(_tracked_modules)


def get_tracked_modules():
    return _tracked_modules.values()
