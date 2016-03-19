'''
Created on 30/04/2011

@author: mikel
'''
from _spotify import album as _album, artist as _artist

from spotify.utils.decorators import synchronized

from spotify import artist

from image import ImageSize

import binascii



class AlbumType:
    Album = 0
    Single = 1
    Compilation = 2
    Unknown = 3



class Album:
    __album_struct = None
    __album_interface = None
    
    
    def __init__(self, album_struct):
        self.__album_struct = album_struct
        self.__album_interface = _album.AlbumInterface()
    
    
    @synchronized
    def is_loaded(self):
        return self.__album_interface.is_loaded(self.__album_struct)
    
    
    @synchronized
    def is_available(self):
        return self.__album_interface.is_available(self.__album_struct)
    
    
    @synchronized
    def artist(self):
        #Increment the refcount so it doesn't get stolen from us
        artist_struct = self.__album_interface.artist(self.__album_struct)
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    @synchronized
    def cover(self, size=ImageSize.Normal):
        res = self.__album_interface.cover(self.__album_struct, size)
        if res:
            return binascii.b2a_hex(buffer(res.contents))
    
    
    @synchronized
    def name(self):
        return self.__album_interface.name(self.__album_struct)
    
    
    @synchronized
    def year(self):
        return self.__album_interface.year(self.__album_struct)
    
    
    @synchronized
    def type(self):
        return self.__album_interface.type(self.__album_struct)
    
    
    @synchronized
    def __del__(self):
        self.__album_interface.release(self.__album_struct)
    
    
    def get_struct(self):
        return self.__album_struct
