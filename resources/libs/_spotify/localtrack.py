import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface



class LocalTrackInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_localtrack_create',
            ctypes.c_void_p,
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int
        )(*args)
