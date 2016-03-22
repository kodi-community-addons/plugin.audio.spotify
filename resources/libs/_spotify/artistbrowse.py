import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Callbacks
artistbrowse_complete_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class ArtistBrowseInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_artistbrowse_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, artistbrowse_complete_cb, ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_artistbrowse_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_artistbrowse_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_artistbrowse_artist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def num_portraits(self, *args):
        return self._get_func(
            'sp_artistbrowse_num_portraits',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def portrait(self, *args):
        return self._get_func(
            'sp_artistbrowse_portrait',
            ctypes.POINTER(ctypes.c_byte * 20),
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_tracks(self, *args):
        return self._get_func(
            'sp_artistbrowse_num_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def track(self, *args):
        return self._get_func(
            'sp_artistbrowse_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def num_tophit_tracks(self, *args):
        return self._get_func(
            'sp_artistbrowse_num_tophit_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
    
    
    def tophit_track(self, *args):
        return self._get_func(
            'sp_artistbrowse_tophit_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def num_albums(self, *args):
        return self._get_func(
            'sp_artistbrowse_num_albums',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def album(self, *args):
        return self._get_func(
            'sp_artistbrowse_album',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_similar_artists(self, *args):
        return self._get_func(
            'sp_artistbrowse_num_similar_artists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def similar_artist(self, *args):
        return self._get_func(
            'sp_artistbrowse_similar_artist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def biography(self, *args):
        return self._get_func(
            'sp_artistbrowse_biography',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)
    
    
    def backend_request_duration(self, *args):
        return self._get_func(
            'sp_artistbrowse_backend_request_duration',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_artistbrowse_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_artistbrowse_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
