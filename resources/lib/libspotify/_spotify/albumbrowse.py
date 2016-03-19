import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Callbacks
albumbrowse_complete_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class AlbumBrowseInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_albumbrowse_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, albumbrowse_complete_cb, ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_albumbrowse_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_albumbrowse_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def album(self, *args):
        return self._get_func(
            'sp_albumbrowse_album',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_albumbrowse_artist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def num_copyrights(self, *args):
        return self._get_func(
            'sp_albumbrowse_num_copyrights',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def copyright(self, *args):
        return self._get_func(
            'sp_albumbrowse_copyright',
            ctypes.c_char_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_tracks(self, *args):
        return self._get_func(
            'sp_albumbrowse_num_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def track(self, *args):
        return self._get_func(
            'sp_albumbrowse_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def review(self, *args):
        return self._get_func(
            'sp_albumbrowse_review',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def backend_request_duration(self, *args):
        return self._get_func(
            'sp_albumbrowse_backend_request_duration',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_albumbrowse_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_albumbrowse_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
