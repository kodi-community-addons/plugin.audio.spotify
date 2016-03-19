import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, subscribers as _subscribers, bool_type


#Structure definitions
class callbacks(ctypes.Structure):
    pass


#Callbacks
cb_tracks_added = callback(
    None,
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_void_p
)

cb_tracks_removed = callback(
    None,
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
    ctypes.c_int, ctypes.c_void_p
)

cb_tracks_moved = callback(
    None,
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
    ctypes.c_int, ctypes.c_int, ctypes.c_void_p
)

cb_playlist_renamed = callback(None, ctypes.c_void_p, ctypes.c_void_p)
cb_playlist_state_changed = callback(None, ctypes.c_void_p, ctypes.c_void_p)

cb_playlist_update_in_progress = callback(
    None, ctypes.c_void_p, bool_type, ctypes.c_void_p
)

cb_playlist_metadata_updated = callback(None, ctypes.c_void_p, ctypes.c_void_p)

cb_track_created_changed = callback(
    None,
    ctypes.c_void_p, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)

cb_track_seen_changed = callback(
    None, ctypes.c_void_p, ctypes.c_int, bool_type, ctypes.c_void_p
)

cb_description_changed = callback(
    None, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p
)

cb_image_changed = callback(
    None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_byte), ctypes.c_void_p
)

cb_track_message_changed = callback(
    None, ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p
)

cb_subscribers_changed = callback(None, ctypes.c_void_p, ctypes.c_void_p)
        
        
#Completion of structure defs
callbacks._fields_ = [
   ("tracks_added", cb_tracks_added),
   ("tracks_removed", cb_tracks_removed),
   ("tracks_moved", cb_tracks_moved),
   ("playlist_renamed", cb_playlist_renamed),
   ("playlist_state_changed", cb_playlist_state_changed),
   ("playlist_update_in_progress", cb_playlist_update_in_progress),
   ("playlist_metadata_updated", cb_playlist_metadata_updated),
   ("track_created_changed", cb_track_created_changed),
   ("track_seen_changed", cb_track_seen_changed),
   ("description_changed", cb_description_changed),
   ("image_changed", cb_image_changed),
   ("track_message_changed", cb_track_message_changed),
   ("subscribers_changed", cb_subscribers_changed),
]



class PlaylistInterface(LibSpotifyInterface):
    def _init__(self):
        LibSpotifyInterface.__init__(self)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_playlist_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def add_callbacks(self, *args):
        return self._get_func(
            'sp_playlist_add_callbacks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(callbacks), ctypes.c_void_p
        )(*args)


    def remove_callbacks(self, *args):
        return self._get_func(
            'sp_playlist_remove_callbacks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(callbacks), ctypes.c_void_p
        )(*args)


    def num_tracks(self, *args):
        return self._get_func(
            'sp_playlist_num_tracks',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def track(self, *args):
        return self._get_func(
            'sp_playlist_track',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def track_create_time(self, *args):
        return self._get_func(
            'sp_playlist_track_create_time',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def track_creator(self, *args):
        return self._get_func(
            'sp_playlist_track_creator',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def track_seen(self, *args):
        return self._get_func(
            'sp_playlist_track_seen',
            bool_type,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def track_set_seen(self, *args):
        return self._get_func(
            'sp_playlist_track_set_seen',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int, bool_type
        )(*args)


    def track_message(self, *args):
        return self._get_func(
            'sp_playlist_track_message',
            ctypes.c_char_p,
            ctypes.c_void_p, ctypes.c_int
        )(*args)


    def name(self, *args):
        return self._get_func(
            'sp_playlist_name',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def rename(self, *args):
        return self._get_func(
            'sp_playlist_rename',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_char_p
        )(*args)


    def owner(self, *args):
        return self._get_func(
            'sp_playlist_owner',
            ctypes.c_void_p,
            ctypes.c_void_p
        )(*args)


    def is_collaborative(self, *args):
        return self._get_func(
            'sp_playlist_is_collaborative',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def set_collaborative(self, *args):
        return self._get_func(
            'sp_playlist_set_collaborative',
            ctypes.c_int,
            ctypes.c_void_p, bool_type
        )(*args)


    def set_autolink_tracks(self, *args):
        return self._get_func(
            'sp_playlist_set_autolink_tracks',
            ctypes.c_int,
            ctypes.c_void_p, bool_type
        )(*args)


    def get_description(self, *args):
        return self._get_func(
            'sp_playlist_get_description',
            ctypes.c_char_p,
            ctypes.c_void_p
        )(*args)


    def get_image(self, *args):
        return self._get_func(
            'sp_playlist_get_image',
            bool_type,
            ctypes.c_void_p, ctypes.c_byte * 20
        )(*args)


    def has_pending_changes(self, *args):
        return self._get_func(
            'sp_playlist_has_pending_changes',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def add_tracks(self, *args):
        return self._get_func(
            'sp_playlist_add_tracks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int, ctypes.c_int, ctypes.c_void_p
        )(*args)


    def remove_tracks(self, *args):
        return self._get_func(
            'sp_playlist_remove_tracks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int
        )(*args)


    def reorder_tracks(self, *args):
        return self._get_func(
            'sp_playlist_reorder_tracks',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int
        )(*args)


    def num_subscribers(self, *args):
        return self._get_func(
            'sp_playlist_num_subscribers',
            ctypes.c_uint,
            ctypes.c_void_p
        )(*args)


    def subscribers(self, *args):
        return self._get_func(
            'sp_playlist_subscribers',
            ctypes.POINTER(_subscribers),
            ctypes.c_void_p
        )(*args)


    def subscribers_free(self, *args):
        return self._get_func(
            'sp_playlist_subscribers_free',
            ctypes.c_int,
            ctypes.POINTER(_subscribers)
        )(*args)


    def update_subscribers(self, *args):
        return self._get_func(
            'sp_playlist_update_subscribers',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def is_in_ram(self, *args):
        return self._get_func(
            'sp_playlist_is_in_ram',
            bool_type,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def set_in_ram(self, *args):
        return self._get_func(
            'sp_playlist_set_in_ram',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, bool_type
        )(*args)


    def create(self, *args):
        return self._get_func(
            'sp_playlist_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def set_offline_mode(self, *args):
        return self._get_func(
            'sp_playlist_set_offline_mode',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, bool_type
        )(*args)


    def get_offline_status(self, *args):
        return self._get_func(
            'sp_playlist_get_offline_status',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def get_offline_download_completed(self, *args):
        return self._get_func(
            'sp_playlist_get_offline_download_completed',
            ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_playlist_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_playlist_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
