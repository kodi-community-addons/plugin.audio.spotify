'''
Created on 07/11/2010

@author: mikel
'''
import ctypes

from _spotify import track as _track, album as _album, artist as _artist

import artist, album, link

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator



class TrackAvailability:
    Unavailable = 0
    Available = 1
    NotStreamable = 2
    BannedByArtist = 3



class TrackOfflineStatus:
    No = 0
    Waiting = 1
    Downloading = 2
    Done = 3
    Error = 4
    DoneExpired = 5
    LimitExceeded = 6
    DoneResync = 7



@synchronized
def set_starred(session, tracks, star):
    track_arr = (ctypes.c_void_p * len(tracks))()
    ti = _track.TrackInterface()
    
    for index, item in enumerate(tracks):
        track_arr[index] = item.get_struct()
    
    ti.set_starred(
        session.get_struct(), track_arr, len(tracks), star
    )



class Track:
    __track_struct = None
    __track_interface = None
    
    
    def __init__(self, track_struct):
        self.__track_struct = track_struct
        self.__track_interface = _track.TrackInterface()
    
    
    @synchronized
    def is_loaded(self):
        return self.__track_interface.is_loaded(self.__track_struct)
    
    
    @synchronized
    def error(self):
        return self.__track_interface.error(self.__track_struct)
    
    
    @synchronized
    def offline_get_status(self):
        return self.__track_interface.offline_get_status(self.__track_struct)
    
    
    @synchronized
    def get_availability(self, session):
        return self.__track_interface.get_availability(
            session.get_struct(), self.__track_struct
        )
    
    
    @synchronized
    def is_local(self, session):
        return self.__track_interface.is_local(
            session.get_struct(), self.__track_struct
        )
    
    
    @synchronized
    def is_autolinked(self, session):
        return self.__track_interface.is_autolinked(
            session.get_struct(), self.__track_struct
        )
    
    
    @synchronized
    def get_playable(self, session):
        track_struct = self.__track_interface.get_playable(
            session.get_struct(), self.__track_struct
        )
        
        if track_struct is not None:
            self.__track_interface.add_ref(track_struct)
            return Track(track_struct)
    
    
    @synchronized
    def is_placeholder(self):
        return self.__track_interface.is_placeholder(self.__track_struct)
    
    
    @synchronized
    def is_starred(self, session):
        return self.__track_interface.is_starred(
            session.get_struct(), self.__track_struct
        )
    
    
    @synchronized
    def num_artists(self):
        return self.__track_interface.num_artists(self.__track_struct)
    
    
    @synchronized
    def artist(self, index):
        artist_struct = self.__track_interface.artist(
            self.__track_struct, index
        )
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    def artists(self):
        return CallbackIterator(self.num_artists, self.artist)
    
    
    @synchronized
    def album(self):
        album_struct = self.__track_interface.album(self.__track_struct)
        
        if album_struct is not None:
            ai = _album.AlbumInterface()
            ai.add_ref(album_struct)
            return album.Album(album_struct)
    
    
    @synchronized
    def name(self):
        return self.__track_interface.name(self.__track_struct)
    
    
    @synchronized
    def duration(self):
        return self.__track_interface.duration(self.__track_struct)
    
    
    @synchronized
    def popularity(self):
        return self.__track_interface.popularity(self.__track_struct)
    
    
    @synchronized
    def disc(self):
        return self.__track_interface.disc(self.__track_struct)
    
    
    @synchronized
    def index(self):
        return self.__track_interface.index(self.__track_struct)
    
    
    def __str__(self):
        l = link.create_from_track(self)
        return l.as_string()
    
    
    @synchronized
    def __del__(self):
        self.__track_interface.release(self.__track_struct)
    
    
    def get_struct(self):
        return self.__track_struct
