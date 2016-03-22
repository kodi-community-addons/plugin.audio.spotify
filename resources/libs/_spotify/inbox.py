import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback


#Callbacks
inboxpost_complete_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class InboxInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def post_tracks(self, *args):
        return self._get_func(
            'sp_inbox_post_tracks',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.c_char_p,
            inboxpost_complete_cb, ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_inbox_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_inbox_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_inbox_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
