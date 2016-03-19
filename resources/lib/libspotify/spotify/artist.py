'''
Created on 30/04/2011

@author: mikel
'''
from _spotify import artist as _artist

from spotify.utils.decorators import synchronized

from image import ImageSize

import binascii



class Artist:
    __artist_struct = None
    __artist_interface = None
    
    
    def __init__(self, artist_struct):
        self.__artist_struct = artist_struct
        self.__artist_interface = _artist.ArtistInterface()

    
    @synchronized
    def name(self):
        return self.__artist_interface.name(self.__artist_struct)
    
    
    @synchronized
    def is_loaded(self):
        return self.__artist_interface.is_loaded(self.__artist_struct)
    
    
    @synchronized
    def portrait(self, size=ImageSize.Normal):
        res = self.__artist_interface.portrait(self.__artist_struct, size)
        if res:
            return binascii.b2a_hex(buffer(res.contents))
    
    
    @synchronized
    def __del__(self):
        self.__artist_interface.release(self.__artist_struct)
    
    
    def get_struct(self):
        return self.__artist_struct
