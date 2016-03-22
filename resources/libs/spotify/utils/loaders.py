'''
Created on 11/08/2012

@author: mazkolain
'''
from spotify import LibSpotifyError
from spotify.albumbrowse import Albumbrowse, AlbumbrowseCallbacks
from spotify.session import SessionCallbacks
from spotify.image import ImageCallbacks
from threading import Event



class LoadTimeoutError(LibSpotifyError):
    pass



class _LoadAlbumCallbacks(AlbumbrowseCallbacks):
    __event = None
    
    
    def __init__(self):
        self.__event = Event()
    
    
    def albumbrowse_complete(self, albumbrowse):
        self.__event.set()
    
    
    def wait(self, albumbrowse, timeout=None):
        if not albumbrowse.is_loaded():
            self.__event.wait(timeout)
        
        return albumbrowse.is_loaded()



def load_albumbrowse(session, album, timeout=5, ondelay=None):
    
    #Check a valid number on timeout
    if timeout <= 1:
        raise ValueError('Timeout value must be higher than one second.')
    
    callbacks = _LoadAlbumCallbacks()
    albumbrowse = Albumbrowse(session, album, callbacks)
    
    #Wait a single second for the album
    if callbacks.wait(albumbrowse, 1):
        return albumbrowse
    
    #It needs more time...
    else:
        
        #Notify about the delay
        if ondelay is not None:
            ondelay()
        
        #And keep waiting
        if callbacks.wait(albumbrowse, timeout - 1):
            return albumbrowse
    
        else:
            raise LoadTimeoutError('Albumbrowse object failed to load')



class _TrackLoadCallback(SessionCallbacks):
    __event = None
    __track = None
    
    
    def __init__(self, track):
        self.__track = track
        self.__event = Event()
    
    
    def metadata_updated(self, session):
        if self.__track.is_loaded():
            self.__event.set()
    
    
    def wait(self, timeout=None):
        if not self.__track.is_loaded():
            self.__event.wait(timeout)
        
        return self.__track.is_loaded()



def load_track(session, track, timeout=5, ondelay=None):
    
    #Check a valid number on timeout
    if timeout <= 1:
        raise ValueError('Timeout value must be higher than one second.')
    
    if not track.is_loaded():
    
        #Set callbacks for loading the track
        callbacks = _TrackLoadCallback(track)
        session.add_callbacks(callbacks)
        
        try:
            #Wait a single second
            if not callbacks.wait(timeout):
                
                #Notify about the delay
                if ondelay is not None:
                    ondelay()
                
                #And keep waiting
                if not callbacks.wait(timeout - 1):
                    raise LoadTimeoutError('Track object failed to load.')
        
        finally:
            #Remove that callback, or will be around forever
            session.remove_callbacks(callbacks)
    
    return track



class _ImageLoadCallbacks(ImageCallbacks):
    __event = None
    __image = None
    
    
    def __init__(self, image):
        self.__event = Event()
        self.__image = image
    
    
    def image_loaded(self, image):
        self.__event.set()
    
    
    def wait(self, timeout=None):
        if not self.__image.is_loaded():
            self.__event.wait(timeout)
        
        return self.__image.is_loaded()



def load_image(image, timeout=5, ondelay=None):
    
    #Check a valid number on timeout
    if timeout <= 1:
        raise ValueError('Timeout value must be higher than one second.')
    
    if not image.is_loaded():
    
        #Set callbacks for loading the track
        callbacks = _ImageLoadCallbacks(image)
        image.add_load_callback(callbacks)
        
        try:
            #Wait a single second
            if not callbacks.wait(timeout):
                
                #Notify about the delay
                if ondelay is not None:
                    ondelay()
                
                #And keep waiting
                if not callbacks.wait(timeout - 1):
                    raise LoadTimeoutError('Image object failed to load.')
        
        finally:
            #Remove that callback, or will be around forever
            image.remove_load_callback(callbacks)
    
    return image
