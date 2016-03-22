'''
Created on 10/04/2011

@author: mikel
'''
import ctypes

from spotify import track, user, DuplicateCallbackError, UnknownCallbackError, handle_sp_error

from _spotify import playlist as _playlist, track as _track, user as _user

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator

from spotify.utils.weakmethod import WeakMethod

import weakref

import binascii



class PlaylistType:
    Playlist = 0
    StartFolder = 1
    EndFolder = 2
    Placeholder = 3



class PlaylistOfflineStatus:
    No = 0
    Yes = 1
    Downloading = 2
    Waiting = 3



class ProxyPlaylistCallbacks:
    _playlist = None
    _callbacks = None
    _callback_struct = None
    _callback_struct_ptr = None
    
    def __init__(self, playlist, callbacks):
        self._playlist = weakref.proxy(playlist)
        self._callbacks = callbacks
        self._callback_struct = _playlist.callbacks(
            _playlist.cb_tracks_added(WeakMethod(self._tracks_added)),
            _playlist.cb_tracks_removed(WeakMethod(self._tracks_removed)),
            _playlist.cb_tracks_moved(WeakMethod(self._tracks_moved)),
            _playlist.cb_playlist_renamed(WeakMethod(self._playlist_renamed)),
            _playlist.cb_playlist_state_changed(WeakMethod(self._playlist_state_changed)),
            _playlist.cb_playlist_update_in_progress(WeakMethod(self._playlist_update_in_progress)),
            _playlist.cb_playlist_metadata_updated(WeakMethod(self._playlist_metadata_updated)),
            _playlist.cb_track_created_changed(WeakMethod(self._track_created_changed)),
            _playlist.cb_track_seen_changed(WeakMethod(self._track_seen_changed)),
            _playlist.cb_description_changed(WeakMethod(self._description_changed)),
            _playlist.cb_image_changed(WeakMethod(self._image_changed)),
            _playlist.cb_track_message_changed(WeakMethod(self._track_message_changed)),
            _playlist.cb_subscribers_changed(WeakMethod(self._subscribers_changed)),
        )
        self._callback_struct_ptr = ctypes.pointer(self._callback_struct)
    
    #Callback proxies
    def _tracks_added(self, playlist, tracks, num_tracks, position, userdata):
        self._callbacks.tracks_added(self._playlist, tracks, position)
    
    def _tracks_removed(self, playlist, tracks, num_tracks, userdata):
        self._callbacks.tracks_removed(self._playlist, tracks)
    
    def _tracks_moved(self, playlist, tracks, num_tracks, new_position, userdata):
        self._callbacks.tracks_moved(self._playlist, tracks, new_position)
    
    def _playlist_renamed(self, playlist, userdata):
        self._callbacks.playlist_renamed(self._playlist)
    
    def _playlist_state_changed(self, playlist, userdata):
        self._callbacks.playlist_state_changed(self._playlist)
    
    def _playlist_update_in_progress(self, playlist, done, userdata):
        self._callbacks.playlist_update_in_progress(
            self._playlist, done
        )
    
    def _playlist_metadata_updated(self, playlist, userdata):
        self._callbacks.playlist_metadata_updated(self._playlist)
    
    def _track_created_changed(self, playlist, position, c_user, when, userdata):
        self._callbacks.track_created_changed(
            self._playlist, position, user.User(c_user), when
        )
    
    def _track_seen_changed(self, playlist, position, seen, userdata):
        self._callbacks.track_seen_changed(self._playlist, position, seen)
    
    def _description_changed(self, playlist, desc, userdata):
        self._callbacks.description_changed(self._playlist, desc)
    
    def _image_changed(self, playlist, image, userdata):
        self._callbacks.image_changed(self._playlist, image)
    
    def _track_message_changed(self, playlist, position, message, userdata):
        self._callbacks.track_message_changed(
            self._playlist, position, message
        )
    
    def _subscribers_changed(self, playlist, userdata):
        self._callbacks.subscribers_changed(
            self._playlist
        )
    
    def get_callbacks(self):
        return self._callbacks
    
    #Build up the struct
    def get_callback_struct_ptr(self):
        return self._callback_struct_ptr


class PlaylistCallbacks:
    def tracks_added(self, playlist, tracks, position):
        pass
    
    def tracks_removed(self, playlist, tracks):
        pass
    
    def tracks_moved(self, playlist, tracks, new_position):
        pass
    
    def playlist_renamed(self, playlist):
        pass
    
    def playlist_state_changed(self, playlist):
        pass
    
    def playlist_update_in_progress(self, playlist, done):
        pass
    
    def playlist_metadata_updated(self, playlist):
        pass
    
    def track_created_changed(self, playlist, position, user, when):
        pass
    
    def track_seen_changed(self, playlist, position, seen):
        pass
    
    def description_changed(self, playlist, desc):
        pass
    
    def image_changed(self, playlist, image):
        pass
    
    def track_message_changed(self, playlist, position, message):
        pass
    
    def subscribers_changed(self, playlist):
        pass



@synchronized
def create(session, link):
    pi = _playlist.PlaylistInterface()
    return pi.create(session.get_struct(), link.get_struct())



class Playlist:
    __playlist_struct = None
    __playlist_interface = None
    __callbacks = None
    
    
    def __init__(self, playlist_struct):
        self.__playlist_struct = playlist_struct
        self.__playlist_interface = _playlist.PlaylistInterface()
        self.__callbacks = {}
    
    
    @synchronized
    def is_loaded(self):
        return self.__playlist_interface.is_loaded(self.__playlist_struct)
    
    
    @synchronized
    def add_callbacks(self, callbacks):
        cb_id = id(callbacks)
        
        if cb_id in self.__callbacks:
            raise DuplicateCallbackError()
        
        else:
            proxy = ProxyPlaylistCallbacks(self, callbacks)
            self.__callbacks[cb_id] = proxy
            self.__playlist_interface.add_callbacks(
                self.__playlist_struct, proxy.get_callback_struct_ptr(), None
            )
    
    
    @synchronized
    def remove_callbacks(self, callbacks):
        cb_id = id(callbacks)
        
        if cb_id not in self.__callbacks:
            raise UnknownCallbackError()
        
        else:
            ptr = self.__callbacks[cb_id].get_callback_struct_ptr()
            self.__playlist_interface.remove_callbacks(
                self.__playlist_struct, ptr, None
            )
            del self.__callbacks[cb_id]
    
    
    def remove_all_callbacks(self):
        for proxy in self.__callbacks.values():
            self.remove_callbacks(proxy.get_callbacks())
    
    
    @synchronized
    def num_tracks(self):
        return self.__playlist_interface.num_tracks(self.__playlist_struct)
    
    
    @synchronized
    def track(self, index):
        track_struct = self.__playlist_interface.track(
            self.__playlist_struct, index
        )
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    
    
    def tracks(self):
        return CallbackIterator(self.num_tracks, self.track)
    
    
    @synchronized
    def track_create_time(self, index):
        return self.__playlist_interface.track_create_time(
            self.__playlist_struct, index
        )
    
    
    @synchronized
    def track_creator(self, index):
        user_struct = self.__playlist_interface.track_creator(
            self.__playlist_struct, index
        )
        
        if user_struct is not None:
            ui = _user.UserInterface()
            ui.add_ref(user_struct)
            return user.User(user_struct)
    
    
    @synchronized
    def track_seen(self, index):
        return self.__playlist_interface.track_seen(
            self.__playlist_struct, index
        )
    
    
    @synchronized
    def track_set_seen(self, index, seen):
        handle_sp_error(
            self.__playlist_interface.track_set_seen(
                self.__playlist_struct, index, seen
            )
        )
    
    
    @synchronized
    def track_message(self, index):
        return self.__playlist_interface.track_message(
            self.__playlist_struct, index
        )
    
    
    @synchronized
    def name(self):
        return self.__playlist_interface.name(self.__playlist_struct)
    
    
    @synchronized
    def rename(self, new_name):
        handle_sp_error(
            self.__playlist_interface.rename(self.__playlist_struct, new_name)
        )
    
    
    @synchronized
    def owner(self):
        user_struct = self.__playlist_interface.owner(self.__playlist_struct)
        
        if user_struct is not None:
            ui = _user.UserInterface()
            ui.add_ref(user_struct)
            return user.User(user_struct)
    
    
    @synchronized
    def is_collaborative(self):
        return self.__playlist_interface.is_collaborative(
            self.__playlist_struct
        )
    
    
    @synchronized
    def set_collaborative(self, collaborative):
        self.__playlist_interface.set_collaborative(
            self.__playlist_struct, collaborative
        )
    
    
    @synchronized
    def set_autolink_tracks(self, link):
        self.__playlist_interface.set_autolink_tracks(
            self.__playlist_struct, link
        )
    
    
    @synchronized
    def get_description(self):
        return self.__playlist_interface.get_description(
            self.__playlist_struct
        )
    
    
    @synchronized
    def get_image(self):
        imgid = (ctypes.c_byte * 20)()
        result = self.__playlist_interface.get_image(
            self.__playlist_struct, imgid
        )
        
        if result:
            return binascii.b2a_hex(buffer(imgid))
    
    
    @synchronized
    def has_pending_changes(self):
        return self.__playlist_interface.has_pending_changes(
            self.__playlist_struct
        )
    
    
    @synchronized
    def is_in_ram(self, session):
        return self.__playlist_interface.is_in_ram(
            session.get_struct(), self.__playlist_struct
        )
    
    
    @synchronized
    def set_in_ram(self, session, in_ram):
        self.__playlist_interface.set_in_ram(
            session.get_struct(), self.__playlist_struct, in_ram
        )
    
    
    @synchronized
    def add_tracks(self, tracks, position, session):
        arr = (ctypes.c_void_p * len(tracks))()
        
        for index, item in enumerate(tracks):
            arr[index] = item.get_struct()
        
        handle_sp_error(
            self.__playlist_interface.add_tracks(
                self.__playlist_struct,
                ctypes.byref(arr), len(tracks), position,
                session.get_struct()
            )
        )
    
    
    @synchronized
    def remove_tracks(self, tracks):
        arr = (ctypes.c_int * len(tracks))()
        
        for index, item in enumerate(tracks):
            arr[index] = item
        
        handle_sp_error(
            self.__playlist_interface.remove_tracks(
                self.__playlist_struct, ctypes.byref(arr), len(tracks)
            )
        )
    
    
    @synchronized
    def reorder_tracks(self, tracks, new_position):
        arr = (ctypes.c_int * len(tracks))()
        
        for index, item in enumerate(tracks):
            arr[index] = item
        
        handle_sp_error(
            self.__playlist_interface.reorder_tracks(
                self.__playlist_struct,
                ctypes.byref(arr), len(tracks), new_position
            )
        )
    
    
    @synchronized
    def num_subscribers(self):
        return self.__playlist_interface.num_subscribers(
            self.__playlist_struct
        )
    
    
    @synchronized
    def update_subscribers(self):
        self.__playlist_interface.update_subscribers(self.__playlist_struct)
    
    
    #TODO: Rest of the subscribers stuff
    
    
    @synchronized
    def set_offline_mode(self, session, offline):
        self.__playlist_interface.set_offline_mode(
            session.get_struct(), self.__playlist_struct, offline
        )
    
    
    @synchronized
    def get_offline_status(self, session):
        return self.__playlist_interface.get_offline_status(
            session.get_struct(), self.__playlist_struct
        )
    
    
    @synchronized
    def get_offline_download_completed(self, session):
        return self.__playlist_interface.get_offline_download_completed(
            session.get_struct(), self.__playlist_struct
        )
    
    
    @synchronized
    def __del__(self):
        self.remove_all_callbacks()
        self.__playlist_interface.release(self.__playlist_struct)
    
    
    def get_struct(self):
        return self.__playlist_struct
