'''
Created on 29/04/2011

@author: mikel
'''
import ctypes

from _spotify import link as _link, track as _track, user as _user, artist as _artist, album as _album

import album, track, artist, user, image

from spotify.utils.decorators import synchronized



@synchronized
def create_from_string(string):
    li = _link.LinkInterface()
    link_struct = li.create_from_string(string)
    if link_struct is not None:
        return Link(link_struct)


@synchronized
def create_from_track(track, offset = 0):
    li = _link.LinkInterface()
    return Link(li.create_from_track(track.get_struct(), offset))


@synchronized
def create_from_artist(artist):
    li = _link.LinkInterface()
    return Link(li.create_from_artist(artist.get_struct()))


@synchronized
def create_from_artist_portrait(artist, size=image.ImageSize.Normal):
    li = _link.LinkInterface()
    return Link(li.create_from_artist_portrait(artist.get_struct(), size))


@synchronized
def create_from_artistbrowse_portrait(artistbrowse, index):
    li = _link.LinkInterface()
    return Link(
        li.create_from_artistbrowse_portrait(artistbrowse.get_struct(), index)
    )


@synchronized
def create_from_album(album):
    li = _link.LinkInterface()
    return Link(li.create_from_album(album.get_struct()))


@synchronized
def create_from_album_cover(album, size=image.ImageSize.Normal):
    li = _link.LinkInterface()
    return Link(li.create_from_album_cover(album.get_struct(), size))


@synchronized
def create_from_search(search):
    li = _link.LinkInterface()
    return Link(li.create_from_search(search.get_struct()))


@synchronized
def create_from_playlist(playlist):
    li = _link.LinkInterface()
    link_struct = li.create_from_playlist(playlist.get_struct())
    if link_struct is not None:
        return Link(link_struct)


@synchronized
def create_from_user(user):
    li = _link.LinkInterface()
    return Link(li.create_from_user(user.get_struct()))


@synchronized
def create_from_image(image):
    li = _link.LinkInterface()
    return Link(li.create_from_image(image.get_struct()))



class LinkType:
    Invalid = 0
    Track = 1
    Album = 2
    Artist = 3
    Search = 4
    Playlist = 5
    Profile = 6
    Starred = 7
    Localtrack = 8
    Image = 9



class Link:
    __link_struct = None
    __link_interface = None
    
    
    def __init__(self, link_struct):
        self.__link_struct = link_struct
        self.__link_interface = _link.LinkInterface()
    
    
    @synchronized
    def as_string(self):
        buf = (ctypes.c_char * 255)()
        
        #Should check return value?
        self.__link_interface.as_string(self.__link_struct, buf, 255)
        
        return buf.value
    
    
    @synchronized
    def type(self):
        return self.__link_interface.type(self.__link_struct)
    
    
    @synchronized
    def as_track(self):
        track_struct = self.__link_interface.as_track(self.__link_struct)
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct) 
    
    
    @synchronized
    def as_track_and_offset(self):
        offset = ctypes.c_int
        track_struct = self.__link_interface.as_track_and_offset
        
        if track_struct is not None:
            ti = _track.TrackInterface()
            ti.add_ref(track_struct)
            return track.Track(track_struct), offset.value
    
    @synchronized
    def as_album(self):
        album_struct = self.__link_interface.as_album(self.__link_struct)
        
        if album_struct is not None:
            ai = _album.AlbumInterface()
            ai.add_ref(album_struct)
            return album.Album(album_struct)
    
    
    @synchronized
    def as_artist(self):
        #Increment reference count so it's not stolen from us
        artist_struct = self.__link_interface.as_artist(self.__link_struct)
        
        if artist_struct is not None:
            ai = _artist.ArtistInterface()
            ai.add_ref(artist_struct)
            return artist.Artist(artist_struct)
    
    
    @synchronized
    def as_user(self):
        #Increment reference count so it's not stolen from us
        user_struct = self.__link_interface.as_user(self.__link_struct)
        
        if user_struct is not None:
            ui = _user.UserInterface()
            ui.add_ref(user_struct)
            return user.User(user_struct)
    
    
    @synchronized
    def __del__(self):
        self.__link_interface.release(self.__link_struct)
        
        
    def get_struct(self):
        return self.__link_struct
    
    
    def __str__(self):
        return self.as_string()
