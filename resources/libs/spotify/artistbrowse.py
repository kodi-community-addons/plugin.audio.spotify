'''
Created on 21/05/2011

@author: mikel
'''

from _spotify import artistbrowse as _artistbrowse, track as _track, artist as _artist, album as _album

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator

from spotify.utils.weakmethod import WeakMethod

from spotify import artist, album, track

import binascii

import weakref



#FIXME: Check if these are the real values, not published by the API.
class BrowseType:
    Full = 0
    NoTracks = 1
    NoAlbums = 2



class ProxyArtistbrowseCallbacks:
    __artistbrowse = None
    __callbacks = None
    __c_callback = None
    
    
    def __init__(self, artistbrowse, callbacks):
        self.__artistbrowse = weakref.proxy(artistbrowse)
        self.__callbacks = callbacks
        self.__c_callback = _artistbrowse.artistbrowse_complete_cb(
            WeakMethod(self.artistbrowse_complete)
        )
    
    
    def artistbrowse_complete(self, artistbrowse_struct, userdata):
        self.__callbacks.artistbrowse_complete(self.__artistbrowse)
    
    
    def get_c_callback(self):
        return self.__c_callback



class ArtistbrowseCallbacks:
    def artistbrowse_complete(self, artistbrowse):
        pass



class Artistbrowse:
    #The same as on albumbrowse, should honor OOR?
    __artist = None
    __artistbrowse_struct = None
    __artistbrowse_interface = None
    __proxy_callbacks = None
    
    
    @synchronized
    def __init__(self, session, artist, browsetype, callbacks):
        self.__artist = artist
        self.__proxy_callbacks = ProxyArtistbrowseCallbacks(self, callbacks)
        self.__artistbrowse_interface = _artistbrowse.ArtistBrowseInterface()
        self.__artistbrowse_struct = self.__artistbrowse_interface.create(
            session.get_struct(), artist.get_struct(), browsetype,
            self.__proxy_callbacks.get_c_callback(), None
        )
    
    
    @synchronized
    def is_loaded(self):
        return self.__artistbrowse_interface.is_loaded(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def error(self):
        return self.__artistbrowse_interface.error(self.__artistbrowse_struct)
    
    
    def artist(self):
        return self.__artist
    
    
    @synchronized
    def num_portraits(self):
        return self.__artistbrowse_interface.num_portraits(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def portrait(self, index):
        res = self.__artistbrowse_interface.portrait(
            self.__artistbrowse_struct, index
        ).contents
        
        if res is not None:
            return binascii.b2a_hex(buffer(res))
    
    
    def portraits(self):
        return CallbackIterator(self.num_portraits, self.portrait)
    
    
    @synchronized
    def num_tracks(self):
        return self.__artistbrowse_interface.num_tracks(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def track(self, index):
        track_struct = self.__artistbrowse_interface.track(
            self.__artistbrowse_struct, index
        )
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    
    
    def tracks(self):
        return CallbackIterator(self.num_tracks, self.track)
    
    
    @synchronized
    def num_tophit_tracks(self):
        return self.__artistbrowse_interface.num_tophit_tracks(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def tophit_track(self, index):
        track_struct = self.__artistbrowse_interface.tophit_track(
            self.__artistbrowse_struct, index
        )
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    
    
    def tophit_tracks(self):
        return CallbackIterator(self.num_tophit_tracks, self.tophit_track)
    
    
    @synchronized
    def num_albums(self):
        return self.__artistbrowse_interface.num_albums(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def album(self, index):
        album_struct = self.__artistbrowse_interface.album(
            self.__artistbrowse_struct, index
        )
        
        if album_struct is not None:
            ai = _album.AlbumInterface()
            ai.add_ref(album_struct)
            return album.Album(album_struct)
    
    
    def albums(self):
        return CallbackIterator(self.num_albums, self.album)
    
    
    @synchronized
    def num_similar_artists(self):
        return self.__artistbrowse_interface.num_similar_artists(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def similar_artist(self, index):
        artist_struct = self.__artistbrowse_interface.similar_artist(
            self.__artistbrowse_struct, index
        )
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    def similar_artists(self):
        return CallbackIterator(self.num_similar_artists, self.similar_artists)
    
    
    @synchronized
    def biography(self):
        return self.__artistbrowse_interface.biography(
            self.__artistbrowse_struct
        )
    
    
    @synchronized
    def backend_request_duration(self):
        return self.__artistbrowse_interface.backend_request_duration(
            self.__artistbrowse_interface
        )
    
    
    @synchronized
    def __del__(self):
        self.__artistbrowse_interface.release(self.__artistbrowse_struct)
