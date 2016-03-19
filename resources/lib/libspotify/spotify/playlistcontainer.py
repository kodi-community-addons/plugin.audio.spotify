'''
Created on 10/04/2011

@author: mikel
'''
import ctypes

from spotify import DuplicateCallbackError, UnknownCallbackError, handle_sp_error, user, track

from _spotify import playlistcontainer as _playlistcontainer, playlist as _playlist, user as _user

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator

from spotify.utils.weakmethod import WeakMethod

import playlist

import weakref



class ProxyPlaylistContainerCallbacks:
    _container = None
    _callbacks = None
    _callback_struct = None
    _callback_struct_ptr = None
    
    
    def __init__(self, container, callbacks):
        self._container = weakref.proxy(container)
        self._callbacks = callbacks
        self._callback_struct = _playlistcontainer.callbacks(
            _playlistcontainer.cb_playlist_added(WeakMethod(self._playlist_added)),
            _playlistcontainer.cb_playlist_removed(WeakMethod(self._playlist_removed)),
            _playlistcontainer.cb_playlist_moved(WeakMethod(self._playlist_moved)),
            _playlistcontainer.cb_container_loaded(WeakMethod(self._container_loaded)),
        )
        self._callback_struct_ptr = ctypes.pointer(self._callback_struct)
    
    
    def _playlist_added(self, c_container, c_playlist, position, data):
        self._callbacks.playlist_added(
            self._container, self._container.playlist(position), position
        )
    
    
    def _playlist_removed(self, c_container, c_playlist, position, data):
        self._callbacks.playlist_removed(
            self._container, self._container.playlist(position), position
        )
    
    
    def _playlist_moved(self, c_container, c_playlist, position, new_position, data):
        self._callbacks.playlist_moved(
            self._container, self._container.playlist(position),
            position, new_position
        )
    
    
    def _container_loaded(self, container, data):
        self._callbacks.container_loaded(self._container)
        
    
    def get_callbacks(self):
        return self._callbacks
    
    
    def get_callback_struct_ptr(self):
        return self._callback_struct_ptr



class PlaylistContainerCallbacks:
    def playlist_added(self, container, playlist, position):
        pass
    
    def playlist_removed(self, container, playlist, position):
        pass
    
    def playlist_moved(self, container, playlist, position, new_position):
        pass
    
    def container_loaded(self, container):
        pass
        


class PlaylistContainer:
    __container_struct = None
    __container_interface = None
    
    _manager = None
    
    #Just a shortcut callback to avoid subclassing PlaylistContainerCallbacks
    _onload_callback = None
    
    #Keep references to callbacks structs an the like
    _callbacks = None
    
    
    @synchronized
    def __init__(self, container_struct):
        self.__container_struct = container_struct
        self.__container_interface = _playlistcontainer.PlaylistContainerInterface()
        self._playlist_objects = {}
        self._callbacks = {}
    
    
    @synchronized
    def is_loaded(self):
        return self.__container_interface.is_loaded(self.__container_struct)
    
    
    @synchronized
    def add_callbacks(self, callbacks):
        cb_id = id(callbacks)
        if cb_id in self._callbacks:
            raise DuplicateCallbackError()
        
        else:
            proxy = ProxyPlaylistContainerCallbacks(self, callbacks)
            self._callbacks[cb_id] = proxy
            self.__container_interface.add_callbacks(
                self.__container_struct, proxy.get_callback_struct_ptr(), None
            )
    
    
    @synchronized
    def remove_callbacks(self, callbacks):
        cb_id = id(callbacks)
        if cb_id not in self._callbacks:
            raise UnknownCallbackError()
        
        else:
            ptr = self._callbacks[cb_id].get_callback_struct_ptr()
            self.__container_interface.remove_callbacks(
                self.__container_struct, ptr, None
            )
            del self._callbacks[cb_id]
    
    
    def remove_all_callbacks(self):
        for proxy in self._callbacks.values():
            self.remove_callbacks(proxy.get_callbacks())
    
    
    @synchronized
    def num_playlists(self):
        return self.__container_interface.num_playlists(
            self.__container_struct
        )
        
    
    @synchronized
    def playlist(self, pos):
        playlist_struct = self.__container_interface.playlist(
            self.__container_struct, pos
        )
        
        if playlist_struct is not None:
            pi = _playlist.PlaylistInterface()
            pi.add_ref(playlist_struct)
            return playlist.Playlist(playlist_struct)
    
    
    def playlists(self):
        return CallbackIterator(self.num_playlists, self.playlist)
    
    
    @synchronized
    def playlist_type(self, index):
        return self.__container_interface.playlist_type(self.__container_struct, index)
    
    
    @synchronized
    def playlist_folder_name(self, index):
        buf = (ctypes.c_char() * 255)()
        handle_sp_error(
            self.__container_interface.playlist_folder_name(
                self.__container_struct, index, ctypes.byref(buf), 255
            )
        )
        return buf.value
    
    
    @synchronized
    def playlist_folder_id(self, index):
        return self.__container_interface.playlist_folder_id(
            self.__container_struct, index
        )
    
    
    @synchronized
    def add_new_playlist(self, name):
        return playlist.Playlist(
            self.__container_interface.add_new_playlist(
                self.__container_struct, name
            )
        )
    
    
    @synchronized
    def add_playlist(self, link):
        return playlist.Playlist(
            self.__container_interface.add_playlist(
                self.__container_struct, link.get_struct()
            )
        )
    
    
    @synchronized
    def remove_playlist(self, index):
        #FIXME: Should refresh index in _playlist_objects
        handle_sp_error(
            self.__container_interface.remove_playlist(
                self.__container_struct, index
            )
        )
    
    
    @synchronized
    def move_playlist(self, index, new_position, dry_run):
        handle_sp_error(
            self.__container_interface.move_playlist(
                self.__container_struct, new_position, dry_run
            )
        )
    
    
    @synchronized
    def add_folder(self, index, name):
        handle_sp_error(
            self.__container_interface.add_folder(
                self.__container_struct, index, name
            )
        )
    
    
    @synchronized
    def owner(self):
        user_struct = self.__container_interface.owner(
            self.__container_struct
        )
        
        if user_struct is not None:
            ui = _user.UserInterface()
            ui.add_ref(user_struct)
            return user.User(user_struct)
    
    
    @synchronized
    def get_unseen_tracks(self, playlist):
        max_tracks = 100
        track_arr = (ctypes.c_void_p * len(max_tracks))()
        num_tracks = self.__container_interface.get_unseen_tracks(
            self.__container_struct, playlist.get_struct(),
            track_arr, max_tracks
        )
        
        #Build the track object array from the struct
        out_tracks = []
        
        if num_tracks > 0:
            for index in range(num_tracks):
                out_tracks.append(track.Track(track_arr[index]))
        
        return out_tracks
    
    
    @synchronized
    def clear_unseen_tracks(self, playlist):
        self.__container_interface.clear_unseen_tracks(
            self.__container_struct, playlist.get_struct()
        )
    
    
    @synchronized
    def __del__(self):
        self.remove_all_callbacks()
        self.__container_interface.release(self.__container_struct)
    
    
    def __len__(self):
        return self.num_playlists()
    
    
    def get_struct(self):
        return self.__container_struct
