#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc,xbmcgui,xbmcplugin,xbmcaddon
import os.path
import sys
import math
import urlparse
from traceback import print_exc
import threading, thread

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id').decode("utf-8")
ADDON_NAME = ADDON.getAddonInfo('name').decode("utf-8")
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version').decode("utf-8")
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)
SETTING = ADDON.getSetting
SAVESETTING = ADDON.setSetting

libs_dir = os.path.join(ADDON_PATH, "resources/lib")
sys.path.insert(0, libs_dir)
sys.path.insert(0, os.path.join(libs_dir, "libspotify"))

import spotipy
import spotipy.util as util
from utils import logMsg

class Main():

    action = ""
    sp = None
    userid = ""
    usercountry = ""
    offset = ""
    playlistid = ""
    albumid = ""
    trackid = ""
    ownerid = ""
    filter = ""


    def play_track(self):
        WINDOW.setProperty("Spotify.PlayOffset",self.offset)
        WINDOW.setProperty("Spotify.PlayTrack",self.trackid)
        
    def play_album(self):
        WINDOW.setProperty("Spotify.PlayOffset",self.offset)
        WINDOW.setProperty("Spotify.PlayAlbum",self.albumid)
        
    def play_playlist(self):
        alltracks = []
        playlist = self.sp.user_playlist(self.ownerid, self.playlistid,fields="tracks")
        for i, item in enumerate(playlist['tracks']['items']):
            alltracks.append(item['track']['id'])
            if self.trackid == item['track']['id']: self.offset = str(i)
        WINDOW.setProperty("Spotify.PlayOffset",self.offset)
        WINDOW.setProperty("Spotify.PlayTrack",",".join(alltracks))
      
    def get_track_rating(self,popularity):
        if popularity == 0:
            return 0
        else:
            return int(math.ceil(popularity * 6 / 100.0)) - 1  
        
    def add_track_listitem(self,track,playlistid="",albumoffset=""):
        if track.get("images"): thumb = track["images"][0]['url']
        if track['album'].get("images"): thumb = track['album']["images"][0]['url']
        else: thumb = ""
        
        if playlistid: 
            url="plugin://plugin.audio.spotify/?action=play_playlist&trackid=%s&playlistid=%s&ownerid=%s"%(track['id'],playlistid,self.ownerid)
        elif albumoffset: 
            url="plugin://plugin.audio.spotify/?action=play_album&albumid=%s&offset=%s"%(track['album']['id'],albumoffset)
        else:
            url="plugin://plugin.audio.spotify/?action=play_track&trackid=%s"%track['id']
        
        li = xbmcgui.ListItem(
                track['name'],
                path=url,
                iconImage="DefaultMusicSongs.png",
                thumbnailImage=thumb
            )
        li.setProperty('do_not_analyze', 'true')
        
        artists = []
        for artist in track['artists']:
            artists.append(artist["name"])
        
        infolabels = { 
                "title": track["name"],
                "genre": "geen genre",
                "year": 2016,
                "tracknumber": track["track_number"],
                "album": track['album']["name"],
                "artist": " / ".join(artists),
                "rating": str(self.get_track_rating(track["popularity"])),
                "duration": track["duration_ms"]/1000
            }
        li.setInfo( type="Music", infoLabels=infolabels)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)

    def browse_main(self):
        #main listing
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        items = []
        items.append( ("My Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s&applyfilter=my"%(self.userid) ) )
        items.append( ("Followed Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s&applyfilter=followed"%(self.userid) ) )
        items.append( ("All Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s"%(self.userid) ) )
        items.append( ("Featured Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&applyfilter=featured" ) )
        items.append( ("New releases","plugin://plugin.audio.spotify/?action=browse_newreleases" ) )
        items.append( ("Saved Albums","plugin://plugin.audio.spotify/?action=browse_savedalbums" ) )
        items.append( ("Search playlists","plugin://plugin.audio.spotify/?action=search_playlists" ) )
        for item in items:
            li = xbmcgui.ListItem(
                    item[0],
                    path=item[1],
                    iconImage="DefaultMusicAlbums.png"
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item[1], listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def browse_album(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        album = self.sp.album(albumid)
        for i, item in enumerate(album['tracks']['items']):
            self.add_track_listitem(self.sp.track(item["id"]),"",i)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
       
    def browse_playlist(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        playlist = self.sp.user_playlist(self.ownerid, self.playlistid,fields="tracks,next")
        for i, item in enumerate(playlist['tracks']['items']):
            self.add_track_listitem(item['track'],self.playlistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def follow_playlist(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        result = self.sp.follow_playlist(self.ownerid, self.playlistid)
        print result
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def unfollow_playlist(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        self.sp.unfollow_playlist(self.ownerid, self.playlistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def browse_playlists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        if self.filter=="featured":
            playlists = self.sp.featured_playlists(country=self.usercountry)['playlists']
        else:
            playlists = self.sp.user_playlists(self.ownerid)
        for item in playlists['items']:
            if (self.filter=="my" and item['owner']['id'] == self.userid) or (self.filter=="followed" and item['owner']['id'] != self.userid) or (not self.filter=="my" and not self.filter=="followed"):
                playlist = self.sp.user_playlist(item['owner']['id'], item['id'],fields="name,owner,images,id")
                if playlist.get("images"):
                    thumb = playlist["images"][0]['url']
                else: thumb = ""
                url="plugin://plugin.audio.spotify/?action=browse_playlist&playlistid=%s&ownerid=%s"%(playlist['id'],playlist['owner']['id'])
                li = xbmcgui.ListItem(
                        playlist['name'],
                        path=url,
                        iconImage="DefaultMusicAlbums.png",
                        thumbnailImage=thumb
                    )
                li.setProperty('do_not_analyze', 'true')
                li.setProperty('IsPlayable', 'false')
                contextitems = []
                contextitems.append( ("Play","RunPlugin(plugin://plugin.audio.spotify/?action=play_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                if self.filter=="my":
                    contextitems.append( ("Remove playlist","RunPlugin(plugin://plugin.audio.spotify/?action=remove_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                elif self.filter=="followed" or not self.filter and item['owner']['id'] != self.userid:
                    contextitems.append( ("Unfollow playlist","RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                elif item['owner']['id'] != self.userid:
                    followers = self.sp.followers_contains(playlist['owner']['id'],playlist['id'],self.userid)
                    if followers[0] == False:
                        contextitems.append( ("Follow playlist","RunPlugin(plugin://plugin.audio.spotify/?action=follow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                    else:
                        contextitems.append( ("Unfollow playlist","RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                li.addContextMenuItems(contextitems,True)
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def browse_newreleases(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        albums = self.sp.new_releases(country=self.usercountry)
        for item in albums['albums']['items']:
            if item.get("images"):
                thumb = item["images"][0]['url']
            else: thumb = ""
            url="plugin://plugin.audio.spotify/?action=browse_album&albumid=%s"%(item['id'])
            li = xbmcgui.ListItem(
                    item['name'],
                    path=url,
                    iconImage="DefaultMusicAlbums.png",
                    thumbnailImage=thumb
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            contextitems = []
            contextitems.append( ("Play","RunPlugin(plugin://plugin.audio.spotify/?action=play_album&albumid=%s)"%(item['id'])) )
            li.addContextMenuItems(contextitems,True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def browse_savedalbums(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        albums = self.sp.current_user_saved_albums()
        for item in albums['items']:
            item = item["album"]
            if item.get("images"):
                thumb = item["images"][0]['url']
            else: thumb = ""
            url="plugin://plugin.audio.spotify/?action=browse_album&albumid=%s"%(item['id'])
            li = xbmcgui.ListItem(
                    item['name'],
                    path=url,
                    iconImage="DefaultMusicAlbums.png",
                    thumbnailImage=thumb
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            contextitems = []
            contextitems.append( ("Play","RunPlugin(plugin://plugin.audio.spotify/?action=play_album&albumid=%s)"%(item['id'])) )
            li.addContextMenuItems(contextitems,True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def search_playlists(self):
        
    
    def main(self):
        #parse params
        params = urlparse.parse_qs(sys.argv[2][1:].decode("utf-8"))
        logMsg("Parameter string: %s" % sys.argv[2])
        action=params.get("action",None)
        if action: action = "self." + action[0].lower()
        playlistid=params.get("playlistid",None)
        if playlistid: self.playlistid = playlistid[0]
        ownerid=params.get("ownerid",None)
        if ownerid: self.ownerid = ownerid[0]
        trackid=params.get("trackid",None)
        if trackid: self.trackid = trackid[0]
        albumid=params.get("albumid",None)
        if albumid: self.albumid = albumid[0]
        offset=params.get("offset",None)
        if offset: self.offset = offset[0]
        filter=params.get("applyfilter",None)
        if filter: self.filter = filter[0]   
        

        #wait for background service...
        if not WINDOW.getProperty("Spotify.ServiceReady"):
            xbmc.executebuiltin('RunScript("%s")' % os.path.join(ADDON_PATH, 'service.py'))
        
        count = 0
        while not WINDOW.getProperty("Spotify.ServiceReady"):
            logMsg("waiting for service...")
            if count == 30: 
                break
            else:
                xbmc.sleep(250)
                count += 1
                
        if WINDOW.getProperty("Spotify.ServiceReady") != "ready":
            dlg = xbmcgui.Dialog()
            dlg.ok('Login error', 'Login failed, please correct your username and password and try again. Statuscode: ' + WINDOW.getProperty("Spotify.Lasterror"))
            SAVESETTING('username','')
            SAVESETTING('password','')
        else:
            token = util.prompt_for_user_token(SETTING('username'))
            if token:
                self.sp = spotipy.Spotify(auth=token)
                me = self.sp.me()
                self.userid = me.get("id")
                self.usercountry = me.get("country")
                
                if action:
                    eval(action)()
                else:
                    self.browse_main()

        
Main().main()