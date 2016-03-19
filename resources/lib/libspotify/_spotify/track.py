import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, bool_type



class TrackInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)
    
    
    def is_loaded(self, *args):
        return self._get_func(
            'sp_track_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_track_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
    
    
    def offline_get_status(self, *args):
        return self._get_func(
            'sp_track_offline_get_status',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def get_availability(self, *args):
        return self._get_func(
            'sp_track_get_availability',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def is_local(self, *args):
        return self._get_func(
            'sp_track_is_local',
            bool_type,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def is_autolinked(self, *args):
        return self._get_func(
            'sp_track_is_autolinked',
            bool_type,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)
    
    
    def get_playable(self, *args):
        return self._get_func(
            'sp_track_get_playable',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)
    
    
    def is_placeholder(self, *args):
        return self._get_func(
            'sp_track_is_placeholder',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def is_starred(self, *args):
        return self._get_func(
            'sp_track_is_starred',
            bool_type,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def set_starred(self, *args):
        return self._get_func(
            'sp_track_set_starred',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int, bool_type
        )(*args)


    def num_artists(self, *args):
        return self._get_func(
            'sp_track_num_artists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_track_artist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def album(self, *args):
        return self._get_func(
            'sp_track_album',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def name(self, *args):
        return self._get_func(
            'sp_track_name',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def duration(self, *args):
        return self._get_func(
            'sp_track_duration',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def popularity(self, *args):
        return self._get_func(
            'sp_track_popularity',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def disc(self, *args):
        return self._get_func(
            'sp_track_disc',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def index(self, *args):
        return self._get_func(
            'sp_track_index',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_track_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_track_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
