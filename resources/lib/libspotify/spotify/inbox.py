'''
Created on 26/05/2011

@author: mikel
'''
import ctypes

from _spotify import inbox as _inbox

from spotify.utils.decorators import synchronized
from spotify.utils.weakmethod import WeakMethod



class ProxyInboxpostCallbacks:
    __inbox = None
    __callbacks = None
    __c_callback = None
    
    
    def __init__(self, inbox, callbacks):
        self.__inbox = inbox
        self.__callbacks = callbacks
        self.__c_callback = _inbox.inboxpost_complete_cb(
            WeakMethod(self.inboxpost_complete)
        )
    
    
    def inboxpost_complete(self, inbox_struct, userdata):
        self.__callbacks.inboxpost_complete(self.__inbox)
    
    
    def get_c_callback(self):
        return self.__c_callback



class InboxpostCallbacks:
    def inboxpost_complete(self, inbox):
        pass



class Inbox:
    __inbox_struct = None
    __inbox_interface = None
    __proxy_callbacks = None
    
    
    def _build_track_array(self, track_list):
        track_arr = (ctypes.c_void_p * len(track_list))()
        for index, item in enumerate(track_list):
            track_arr[index] = item.get_struct()
        return track_arr
    
    
    @synchronized
    def __init__(self, session, user, track_list, message, callbacks):
        self.__proxy_callbacks = ProxyInboxpostCallbacks(self, callbacks)
        self.__inbox_interface = _inbox.InboxInterface()
        self.__inbox_struct = self.__inbox_interface.post_tracks(
            session.get_struct(), user,
            self._build_track_array(track_list), len(track_list),
            message, self.__proxy_callbacks.get_c_callback(), None
        )
    
    
    @synchronized
    def error(self):
        return self.__inbox_interface.error(self.__inbox_struct)
    
    
    @synchronized
    def __del__(self):
        self.__inbox_interface.release(self.__inbox_struct)
