'''
Created on 25/05/2011

@author: mazkolain
'''
from _spotify import search as _search, track as _track, album as _album, artist as _artist
from spotify import track, album, artist, playlist

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator

from spotify.utils.weakmethod import WeakMethod

import weakref



class SearchType:
    Standard = 0
    Suggest = 1



class ProxySearchCallbacks:
    __search = None
    __callbacks = None
    __c_callback = None
    
    
    def __init__(self, search, callbacks):
        self.__search = weakref.proxy(search)
        self.__callbacks = callbacks
        self.__c_callback = _search.search_complete_cb(
            WeakMethod(self.search_complete)
        )
        
        
    def search_complete(self, search_struct, userdata):
        self.__callbacks.search_complete(self.__search)
    
    
    def get_c_callback(self):
        return self.__c_callback



class SearchCallbacks:
    def search_complete(self, result):
        pass



class Search:
    #Not private, so RadioSearchh can see it
    _search_struct = None
    __search_interface = None
    __proxy_callbacks = None
    
    
    @synchronized
    def __init__(self, session, query, track_offset=0, track_count=0, album_offset=0, album_count=0, artist_offset=0, artist_count=0, playlist_offset=0, playlist_count=0, search_type=SearchType.Standard, callbacks=None):
        self.__proxy_callbacks = ProxySearchCallbacks(self, callbacks)
        self.__search_interface = _search.SearchInterface()
        self._search_struct = self.__search_interface.create(
            session.get_struct(), query,
            track_offset, track_count,
            album_offset, album_count,
            artist_offset, artist_count,
            playlist_offset, playlist_count,
            search_type,
            self.__proxy_callbacks.get_c_callback(),
            None
        )
    
    
    @synchronized
    def is_loaded(self):
        return self.__search_interface.is_loaded(self._search_struct)
    
    
    @synchronized
    def error(self):
        return self.__search_interface.error(self._search_struct)
    
    
    @synchronized
    def num_tracks(self):
        return self.__search_interface.num_tracks(self._search_struct)
    
    
    @synchronized
    def track(self, index):
        #Increment the refcount so it doesn't get stolen from us
        track_struct = self.__search_interface.track(self._search_struct, index)
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    
    
    def tracks(self):
        return CallbackIterator(self.num_tracks, self.track)
    
    
    @synchronized
    def num_albums(self):
        return self.__search_interface.num_albums(self._search_struct)
    
    
    @synchronized
    def album(self, index):
        #Increment the refcount so it doesn't get stolen from us
        album_struct = self.__search_interface.album(self._search_struct, index)
        
        if album_struct is not None:
            ai = _album.AlbumInterface()
            ai.add_ref(album_struct)
            return album.Album(album_struct)
    
    
    def albums(self):
        return CallbackIterator(self.num_albums, self.album)
    
    
    @synchronized
    def num_playlists(self):
        return self.__search_interface.num_playlists(
            self.__search_interface
        )
    
    
    @synchronized
    def playlist(self, index):
        playlist_struct = self.__search_interface.playlist(
            self.__search_interface, index
        )
        
        if playlist_struct is not None:
            """
            Do not increment references here, as the official docs say
            that the reference is owned by the caller.
            """
            return playlist.Playlist(playlist_struct)
    
    
    def playlists(self):
        return CallbackIterator(self.num_playlists, self.playlist)
    
    
    @synchronized
    def num_artists(self):
        return self.__search_interface.num_artists(self._search_struct)
    
    
    @synchronized
    def artist(self, index):
        #Increment the refcount so it doesn't get stolen from us
        artist_struct = self.__search_interface.artist(self._search_struct, index)
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    def artists(self):
        return CallbackIterator(self.num_artists, self.artist)
    
    
    @synchronized
    def query(self):
        return self.__search_interface.query(self._search_struct)
    
    
    @synchronized
    def did_you_mean(self):
        return self.__search_interface.did_you_mean(self._search_struct)
    
    
    @synchronized
    def total_tracks(self):
        return self.__search_interface.total_tracks(self._search_struct)
    
    
    @synchronized
    def total_albums(self):
        return self.__search_interface.total_albums(self._search_struct)
    
    
    @synchronized
    def total_artists(self):
        return self.__search_interface.total_artists(self._search_struct)
    
    
    @synchronized
    def total_playlists(self):
        return self.__search_interface.total_playlists(self._search_struct)
    
    
    @synchronized
    def __del__(self):
        self.__search_interface.release(self._search_struct)
