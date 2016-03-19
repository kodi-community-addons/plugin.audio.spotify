import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, bool_type



class ArtistInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def name(self, *args):
        return self._get_func(
            'sp_artist_name',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_artist_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)
    
    
    def portrait(self, *args):
        return self._get_func(
            'sp_artist_portrait',
            ctypes.POINTER(ctypes.c_byte * 20),
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_artist_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_artist_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
