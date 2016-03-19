'''
Created on 18/04/2011

@author: mikel
'''
import threading
import types


class synchronized(object):
    _func = None
    _lock = threading.RLock()
    
    
    def __init__(self, func):
        self._func = func
    
    
    def __call__(self, *args, **kwargs):
        self._lock.acquire()
        
        try:
            result = self._func(*args, **kwargs)
        finally:
            self._lock.release()
        
        return result
    
    
    def __get__(self, obj, ownerClass=None):
        return types.MethodType(self, obj)
    
    
    @staticmethod
    def get_lock():
        return synchronized._lock
