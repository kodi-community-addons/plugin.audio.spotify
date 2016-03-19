import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Structure definitions
class callbacks(ctypes.Structure):
    pass


#Callbacks
cb_playlist_added = callback(
    None,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)

cb_playlist_removed = callback(
    None,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)

cb_playlist_moved = callback(
    None,
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_void_p
)

cb_container_loaded = callback(None, ctypes.c_void_p, ctypes.c_void_p)


#Completion of structure defs
callbacks._fields_ = [
    ("playlist_added", cb_playlist_added),
    ("playlist_removed", cb_playlist_removed),
    ("playlist_moved", cb_playlist_moved),
    ("container_loaded", cb_container_loaded),
]




class PlaylistContainerInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def add_callbacks(self, *args):
        return self._get_func(
            'sp_playlistcontainer_add_callbacks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(callbacks), ctypes.c_void_p
        )(*args)


    def remove_callbacks(self, *args):
        return self._get_func(
            'sp_playlistcontainer_remove_callbacks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(callbacks), ctypes.c_void_p
        )(*args)


    def num_playlists(self, *args):
        return self._get_func(
            'sp_playlistcontainer_num_playlists',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_playlistcontainer_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def playlist(self, *args):
        return self._get_func(
            'sp_playlistcontainer_playlist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def playlist_type(self, *args):
        return self._get_func(
            'sp_playlistcontainer_playlist_type',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def playlist_folder_name(self, *args):
        return self._get_func(
            'sp_playlistcontainer_playlist_folder_name',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        )(*args)


    def playlist_folder_id(self, *args):
        return self._get_func(
            'sp_playlistcontainer_playlist_folder_id',
            ctypes.c_uint64,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def add_new_playlist(self, *args):
        return self._get_func(
            'sp_playlistcontainer_add_new_playlist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_char_p
        )(*args)


    def add_playlist(self, *args):
        return self._get_func(
            'sp_playlistcontainer_add_playlist',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def remove_playlist(self, *args):
        return self._get_func(
            'sp_playlistcontainer_remove_playlist',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def move_playlist(self, *args):
        return self._get_func(
            'sp_playlistcontainer_move_playlist',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, bool_type
        )(*args)


    def add_folder(self, *args):
        return self._get_func(
            'sp_playlistcontainer_add_folder',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p
        )(*args)


    def owner(self, *args):
        return self._get_func(
            'sp_playlistcontainer_owner',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_playlistcontainer_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_playlistcontainer_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
    
    
    def get_unseen_tracks(self, *args):
        return self._get_func(
            'sp_playlistcontainer_get_unseen_tracks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int
        )(*args)
    
    
    def clear_unseen_tracks(self, *args):
        return self._get_func(
            'sp_playlistcontainer_clear_unseen_tracks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)
