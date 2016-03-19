import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Callbacks
search_complete_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class SearchInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_search_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_int,
            search_complete_cb, ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_search_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_search_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def num_tracks(self, *args):
        return self._get_func(
            'sp_search_num_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def track(self, *args):
        return self._get_func(
            'sp_search_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def num_albums(self, *args):
        return self._get_func(
            'sp_search_num_albums',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def album(self, *args):
        return self._get_func(
            'sp_search_album',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def num_playlists(self, *args):
        return self._get_func(
            'sp_search_num_playlists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
    
    
    def playlist(self, *args):
        return self._get_func(
            'sp_search_playlist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def playlist_name(self, *args):
        return self._get_func(
            'sp_search_playlist_name',
            ctypes.c_char_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def playlist_uri(self, *args):
        return self._get_func(
            'sp_search_playlist_uri',
            ctypes.c_char_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def playlist_image_uri(self, *args):
        return self._get_func(
            'sp_search_playlist_image_uri',
            ctypes.c_char_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)
    
    
    def num_artists(self, *args):
        return self._get_func(
            'sp_search_num_artists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def artist(self, *args):
        return self._get_func(
            'sp_search_artist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def query(self, *args):
        return self._get_func(
            'sp_search_query',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def did_you_mean(self, *args):
        return self._get_func(
            'sp_search_did_you_mean',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def total_tracks(self, *args):
        return self._get_func(
            'sp_search_total_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def total_albums(self, *args):
        return self._get_func(
            'sp_search_total_albums',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def total_artists(self, *args):
        return self._get_func(
            'sp_search_total_artists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
    
    
    def total_playlists(self, *args):
        return self._get_func(
            'sp_search_total_playlists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_search_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_search_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
