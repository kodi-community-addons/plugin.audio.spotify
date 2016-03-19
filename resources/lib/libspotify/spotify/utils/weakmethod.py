'''
Created on 21/04/2012

@author: mikel
'''
import weakref, inspect



class WeakMethod():
    __obj = None
    __func = None
    
    
    def __init__(self, method):
        if not inspect.ismethod(method):
            raise RuntimeError('Only bound methods are allowed')
        
        self.__obj = weakref.ref(method.im_self)
        self.__func = weakref.ref(method.im_func)
    
    
    def __call__(self, *args, **kwargs):
        method = getattr(self.__obj(), self.__func().__name__)
        return method(*args, **kwargs)
