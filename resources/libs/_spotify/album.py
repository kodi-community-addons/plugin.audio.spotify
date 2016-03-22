import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, bool_type



class AlbumInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_album_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def is_available(self, *args):
        return self._get_func(
            'sp_album_is_available',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_album_artist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def cover(self, *args):
        return self._get_func(
            'sp_album_cover',
            ctypes.POINTER(ctypes.c_byte * 20),
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def name(self, *args):
        return self._get_func(
            'sp_album_name',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def year(self, *args):
        return self._get_func(
            'sp_album_year',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def type(self, *args):
        return self._get_func(
            'sp_album_type',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_album_add_ref',
            ctypes.c_int,
            ctypes.c_void_p,
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_album_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
