'''
Created on 27/05/2011

@author: mikel
'''
from _spotify import toplistbrowse as _toplistbrowse, artist as _artist, album as _album, track as _track

from spotify.utils.decorators import synchronized

from spotify.utils.iterators import CallbackIterator

from spotify.utils.weakmethod import WeakMethod

from spotify import artist, album, track



def encode_region(country_code):
    uc = country_code.upper()
    if len(uc) != 2:
        raise "The country code must be two chars long"
    else:
        return ord(uc[0]) << 8 | ord(uc[1])



class ToplistType:
    Artists = 0
    Albums = 1
    Tracks = 2



class ToplistRegion:
    Everywhere = 0
    User = 1



class ProxyToplistbrowseCallbacks:
    __toplistbrowse = None
    __callbacks = None
    __c_callback = None
    
    
    def __init__(self, toplistbrowse, callbacks):
        self.__toplistbrowse = toplistbrowse
        self.__callbacks = callbacks
        self.__c_callback = _toplistbrowse.toplistbrowse_complete_cb(
            WeakMethod(self.toplistbrowse_complete)
        )
    
    
    def toplistbrowse_complete(self, toplisbrowse_struct, userdata):
        self.__callbacks.toplistbrowse_complete(self.__toplistbrowse)
    
    
    def get_c_callback(self):
        return self.__c_callback



class ToplistbrowseCallbacks:
    def toplistbrowse_complete(self, toplisbrowse):
        pass



class Toplistbrowse:
    __proxy_callbacks = None
    __toplistbrowse_struct = None
    __toplistbrowse_interface = None
    
    
    @synchronized
    def __init__(self, session, type, region, username=None, callbacks=None):
        if callbacks is not None:
            self.__proxy_callbacks = ProxyToplistbrowseCallbacks(
                self, callbacks
            )
            c_callback = self.__proxy_callbacks.get_c_callback()
        else:
            c_callback = None
        
        self.__toplistbrowse_interface = _toplistbrowse.ToplistBrowseInterface()
        self.__toplistbrowse_struct = self.__toplistbrowse_interface.create(
            session.get_struct(), type, region, username, c_callback, None
        )
    
    
    @synchronized
    def is_loaded(self):
        return self.__toplistbrowse_interface.is_loaded(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def error(self):
        return self.__toplistbrowse_interface.error(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def num_artists(self):
        return self.__toplistbrowse_interface.num_artists(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def artist(self, index):
        artist_struct = self.__toplistbrowse_interface.artist(
            self.__toplistbrowse_struct, index
        )
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    def artists(self):
        return CallbackIterator(self.num_artists, self.artist)
    
    
    @synchronized
    def num_albums(self):
        return self.__toplistbrowse_interface.num_albums(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def album(self, index):
        album_struct = self.__toplistbrowse_interface.album(
            self.__toplistbrowse_struct, index
        )
        
        if album_struct is not None:
            ai = _album.AlbumInterface()
            ai.add_ref(album_struct)
            return album.Album(album_struct)
    
    
    def albums(self):
        return CallbackIterator(self.num_albums, self.album)
    
    
    @synchronized
    def num_tracks(self):
        return self.__toplistbrowse_interface.num_tracks(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def track(self, index):
        track_struct = self.__toplistbrowse_interface.track(
            self.__toplistbrowse_struct, index
        )
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    
    
    def tracks(self):
        return CallbackIterator(self.num_tracks, self.track)
    
    
    @synchronized
    def backend_request_duration(self):
        return self.__toplistbrowse_interface.backend_request_duration(
            self.__toplistbrowse_struct
        )
    
    
    @synchronized
    def __del__(self):
        self.__toplistbrowse_interface.release(
            self.__toplistbrowse_struct
        )
