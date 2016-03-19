import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface



class LinkInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create_from_string(self, *args):
        return self._get_func(
            'sp_link_create_from_string',
            ctypes.c_void_p,
            ctypes.c_char_p
        )(*args)


    def create_from_track(self, *args):
        return self._get_func(
            'sp_link_create_from_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def create_from_album(self, *args):
        return self._get_func(
            'sp_link_create_from_album',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_album_cover(self, *args):
        return self._get_func(
            'sp_link_create_from_album_cover',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def create_from_artist(self, *args):
        return self._get_func(
            'sp_link_create_from_artist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_artist_portrait(self, *args):
        return self._get_func(
            'sp_link_create_from_artist_portrait',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def create_from_artistbrowse_portrait(self, *args):
        return self._get_func(
            'sp_link_create_from_artistbrowse_portrait',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_search(self, *args):
        return self._get_func(
            'sp_link_create_from_search',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_playlist(self, *args):
        return self._get_func(
            'sp_link_create_from_playlist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_user(self, *args):
        return self._get_func(
            'sp_link_create_from_user',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def create_from_image(self, *args):
        return self._get_func(
            'sp_link_create_from_image',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def as_string(self, *args):
        return self._get_func(
            'sp_link_as_string',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int
        )(*args)


    def type(self, *args):
        return self._get_func(
            'sp_link_type',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def as_track(self, *args):
        return self._get_func(
            'sp_link_as_track',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def as_track_and_offset(self, *args):
        return self._get_func(
            'sp_link_as_track_and_offset',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def as_album(self, *args):
        return self._get_func(
            'sp_link_as_album',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def as_artist(self, *args):
        return self._get_func(
            'sp_link_as_artist',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def as_user(self, *args):
        return self._get_func(
            'sp_link_as_user',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_link_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_link_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
