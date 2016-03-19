'''
Created on 01/05/2013

@author: mikel
'''
import sys, threading



def event_is_set(event):
    #Return the event's status
    if hasattr(event, 'is_set'):
        return event.is_set()
    
    #Old Python version fallback for the above
    else:
        return event.isSet()



class AtomicEvent:
    
    __event = None
    __is_py32 = None
    
    
    def __init__(self):
        self.__event = threading.Event()
        self.__is_py32 = sys.version_info >= (3, 2)
    
    
    def wait(self, timeout=None):
        event = self.__event
        event.wait(timeout)
        return event_is_set(event)
    
    
    def set(self):
        self.__event.set()
    
    
    def clear(self):
        if not self.__is_py32:
            self.__event = threading.Event()
        else:
            self.__event.clear()
    
    
    def is_set(self):
        return event_is_set(self.__event)
