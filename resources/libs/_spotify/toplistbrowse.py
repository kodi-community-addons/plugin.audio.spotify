import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Callbacks
toplistbrowse_complete_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class ToplistBrowseInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_toplistbrowse_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
            ctypes.c_char_p, toplistbrowse_complete_cb, ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_toplistbrowse_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_toplistbrowse_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_toplistbrowse_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_toplistbrowse_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def num_artists(self, *args):
        return self._get_func(
            'sp_toplistbrowse_num_artists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_toplistbrowse_artist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_albums(self, *args):
        return self._get_func(
            'sp_toplistbrowse_num_albums',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def album(self, *args):
        return self._get_func(
            'sp_toplistbrowse_album',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_tracks(self, *args):
        return self._get_func(
            'sp_toplistbrowse_num_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def track(self, *args):
        return self._get_func(
            'sp_toplistbrowse_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def backend_request_duration(self, *args):
        return self._get_func(
            'sp_toplistbrowse_backend_request_duration',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
