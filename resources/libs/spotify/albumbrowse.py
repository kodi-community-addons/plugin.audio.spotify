'''
Created on 20/05/2011

@author: mikel
'''
from spotify.utils.decorators import synchronized
from spotify.utils.iterators import CallbackIterator
from spotify.utils.weakmethod import WeakMethod

from _spotify import albumbrowse as _albumbrowse
from _spotify import album as _album, artist as _artist, track as _track

from spotify import album, artist, track

import weakref



class Albumtype:
    Album = 0
    Single = 1
    Compilation = 2
    Unknown = 3



class ProxyAlbumbrowseCallbacks:
    __albumbrowse = None
    __callbacks = None
    __c_callback = None
    
    
    def __init__(self, albumbrowse, callbacks):
        self.__albumbrowse = weakref.proxy(albumbrowse)
        self.__callbacks = callbacks
        self.__c_callback = _albumbrowse.albumbrowse_complete_cb(
            WeakMethod(self.albumbrowse_complete)
        )
    
    
    def albumbrowse_complete(self, albumbrowse_struct, userdata):
        self.__callbacks.albumbrowse_complete(self.__albumbrowse)
    
    
    def get_c_callback(self):
        return self.__c_callback



class AlbumbrowseCallbacks:
    def albumbrowse_complete(self, albumbrowse):
        pass



class Albumbrowse:
    #Should we honor OOR?
    __album = None
    __albumbrowse_struct = None
    __albumbrowse_interface = None
    __proxy_callbacks = None
    
    
    @synchronized
    def __init__(self, session, album, callbacks):
        self.__album = album
        self.__albumbrowse_interface = _albumbrowse.AlbumBrowseInterface()
        self.__proxy_callbacks = ProxyAlbumbrowseCallbacks(self, callbacks)
        self.__albumbrowse_struct = self.__albumbrowse_interface.create(
            session.get_struct(), album.get_struct(),
            self.__proxy_callbacks.get_c_callback(), None
        )
    
    
    @synchronized
    def is_loaded(self):
        return self.__albumbrowse_interface.is_loaded(self.__albumbrowse_struct)
    
    
    @synchronized
    def error(self):
        return self.__albumbrowse_interface.error(self.__albumbrowse_struct)
    
    
    def album(self):
        return self.__album
    
    
    @synchronized
    def artist(self):
        #Increment the refcount so it doesn't get stolen from us
        artist_struct = self.__albumbrowse_interface.artist(self.__albumbrowse_struct)
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    @synchronized
    def num_copyrights(self):
        return self.__albumbrowse_interface.num_copyrights(self.__albumbrowse_struct)
    
    
    @synchronized
    def copyright(self, index):
        return self.__albumbrowse_interface.copyright(self.__albumbrowse_struct, index)
    
    
    def copyrights(self):
        return CallbackIterator(self.num_copyrights, self.copyright)
    
    
    @synchronized
    def num_tracks(self):
        return self.__albumbrowse_interface.num_tracks(self.__albumbrowse_struct)
    
    
    @synchronized
    def track(self, index):
        #Increment the refcount so it doesn't get stolen from us
        track_struct = self.__albumbrowse_interface.track(self.__albumbrowse_struct, index)
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct)
    

    def tracks(self):
        return CallbackIterator(self.num_tracks, self.track)
    
    
    @synchronized
    def review(self):
        return self.__albumbrowse_interface.review(self.__albumbrowse_struct)
    
    
    @synchronized
    def backend_request_duration(self):
        return self.__albumbrowse_interface.backend_request_duration(
            self.__albumbrowse_struct
        )
    
    
    @synchronized
    def __del__(self):
        self.__albumbrowse_interface.release(self.__albumbrowse_struct)
