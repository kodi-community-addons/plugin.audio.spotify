# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
from utils import *
add_external_libraries()
import math
import urlparse
import threading, thread
import spotipy
import spotipy.util as util

class Main():

    action = ""
    sp = None
    userid = ""
    usercountry = ""
    offset = 0
    playlistid = ""
    albumid = ""
    trackid = ""
    artistid = ""
    artistname = ""
    ownerid = ""
    filter = ""
    token = ""
    playbackServiceRunning = False
    if xbmc.getCondVisibility("Window.IsActive(MusicLibrary)"):
        limit = 50
    else:
        limit = 25
    params = {}

    def unavailablemessage(self):
        dlg = xbmcgui.Dialog()
        dlg.ok(ADDON_NAME, ADDON.getLocalizedString(11004))
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
    
    def play_android(self):
        if self.ownerid and self.playlistid:
            xbmc.executebuiltin("StartAndroidActivity(,android.intent.action.VIEW,,spotify:user:%s:playlist:%s:play)" %(self.ownerid,self.playlistid))
        elif self.albumid:
            xbmc.executebuiltin("StartAndroidActivity(,android.intent.action.VIEW,,spotify:album:%s:play)" %(self.albumid))
    
    def get_track_rating(self,popularity):
        if popularity == 0:
            return 0
        else:
            return int(math.ceil(popularity * 6 / 100.0)) - 1
        
    def browse_main(self):
        #main listing
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        items = []
        items.append( (ADDON.getLocalizedString(11013),"plugin://plugin.audio.spotify/?action=browse_main_library","DefaultMusicCompilations.png" ) )
        items.append( (ADDON.getLocalizedString(11014),"plugin://plugin.audio.spotify/?action=browse_main_explore","DefaultMusicGenres.png" ) )
        items.append( (xbmc.getLocalizedString(137),"plugin://plugin.audio.spotify/?action=search","DefaultMusicSearch.png" ) )
        for item in items:
            li = xbmcgui.ListItem(
                    item[0],
                    path=item[1],
                    iconImage=item[2]
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.setArt( {"fanart": "special://home/addons/plugin.audio.spotify/fanart.jpg"}  )
            li.addContextMenuItems([],True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def browse_main_library(self):
        #library nodes
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', ADDON.getLocalizedString(11013))
        items = []
        #items.append( ("My Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s&applyfilter=my"%(self.userid) ) )
        #items.append( ("Followed Playlists","plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s&applyfilter=followed"%(self.userid) ) )
        items.append( (xbmc.getLocalizedString(136),"plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s"%(self.userid),"DefaultMusicPlaylists.png" ) )
        items.append( (xbmc.getLocalizedString(132),"plugin://plugin.audio.spotify/?action=browse_savedalbums","DefaultMusicAlbums.png" ) )
        items.append( (xbmc.getLocalizedString(134),"plugin://plugin.audio.spotify/?action=browse_savedtracks","DefaultMusicSongs.png" ) )
        items.append( (xbmc.getLocalizedString(133),"plugin://plugin.audio.spotify/?action=browse_savedartists","DefaultMusicArtists.png" ) )
        for item in items:
            li = xbmcgui.ListItem(
                    item[0],
                    path=item[1],
                    iconImage=item[2]
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.setArt( {"fanart": "special://home/addons/plugin.audio.spotify/fanart.jpg"}  )
            li.addContextMenuItems([],True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def browse_main_explore(self):
        #explore nodes
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', ADDON.getLocalizedString(11014))
        items = []
        items.append( (ADDON.getLocalizedString(11015),"plugin://plugin.audio.spotify/?action=browse_playlists&applyfilter=featured","DefaultMusicPlaylists.png" ) )
        items.append( (ADDON.getLocalizedString(11016),"plugin://plugin.audio.spotify/?action=browse_newreleases","DefaultMusicAlbums.png" ) )
        
        #add categories
        categories = self.sp.categories(country=self.usercountry,limit=50,locale=self.usercountry)
        for item in categories["categories"]["items"]:
            thumb = "DefaultMusicGenre.png"
            for icon in item["icons"]:
                thumb = icon["url"]
                break
            items.append( (item["name"],"plugin://plugin.audio.spotify/?action=browse_category&applyfilter=%s"%(item["id"]),thumb ) )
        
        for item in items:
            li = xbmcgui.ListItem(
                    item[0],
                    path=item[1],
                    iconImage=item[2]
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.setArt( {"fanart": "special://home/addons/plugin.audio.spotify/fanart.jpg"}  )
            li.addContextMenuItems([],True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def getAllAlbumTracks(self,album):
        count = 0
        alltracks = []
        while album["tracks"]["total"] > count:
            alltracks += self.sp.album_tracks(album["id"],market=self.usercountry,limit=50,offset=count)["items"]
            count += 50
        return alltracks
        
    def getAllPlaylistTracks(self,playlist):
        count = 0
        alltracks = []
        while playlist["tracks"]["total"] > count:
            playlists = self.sp.user_playlist_tracks(playlist["owner"]["id"], playlist["id"],market=self.usercountry,fields="",limit=50,offset=count)
            alltracks += playlists["items"]
            total = playlists["total"]
            count += 50
        return alltracks
    
    def browse_album(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        album = self.sp.album(self.albumid,market=self.usercountry)
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', album["name"])
        self.add_track_listitems(tracks=self.getAllAlbumTracks(album),useAlbumOffset=True,fulldetails=True,albumdetails=album)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TRACKNUM)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
     
    def artist_toptracks(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        tracks = self.sp.artist_top_tracks(self.artistid,country=self.usercountry)
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', ADDON.getLocalizedString(11011))
        self.add_track_listitems(tracks=tracks["tracks"])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TRACKNUM)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def related_artists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "artists")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', ADDON.getLocalizedString(11012))
        result = self.sp.artist_related_artists(self.artistid)
        self.add_artist_listitems(result['artists'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def browse_playlist(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        playlist = self.sp.user_playlist(self.ownerid, self.playlistid,market=self.usercountry, fields="tracks(total),name,owner(id),id")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', playlist["name"])
        self.add_track_listitems(self.getAllPlaylistTracks(playlist),playlistid=self.playlistid)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def browse_category(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        category = self.sp.category(self.filter,country=self.usercountry,locale=self.usercountry)
        playlists = self.sp.category_playlists(self.filter,country=self.usercountry,limit=self.limit,offset=self.offset)
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', category["name"])
        self.add_playlist_listitems(playlists['playlists']['items'])
        self.addNextButton(playlists['playlists']['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def follow_playlist(self):
        result = self.sp.follow_playlist(self.ownerid, self.playlistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def add_track_to_playlist(self):
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        playlists = self.sp.user_playlists(self.userid,limit=50,offset=0)
        ownplaylists = []
        ownplaylistnames = []
        for playlist in playlists['items']:
            if playlist["owner"]["id"] == self.userid:
                ownplaylists.append(playlist)
                ownplaylistnames.append(playlist["name"])
        ownplaylistnames.append(xbmc.getLocalizedString(525))
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        select = xbmcgui.Dialog().select(xbmc.getLocalizedString(524),ownplaylistnames)
        if select != -1 and ownplaylistnames[select] == xbmc.getLocalizedString(525):
            #create new playlist...
            kb = xbmc.Keyboard('', xbmc.getLocalizedString(21381))
            kb.setHiddenInput(False)
            kb.doModal()
            if kb.isConfirmed():
                name = kb.getText()
                playlist = self.sp.user_playlist_create(self.userid,name,False)
                self.sp.user_playlist_add_tracks(self.userid,playlist["id"],[self.trackid])
        elif select != -1:
            playlist = ownplaylists[select]
            self.sp.user_playlist_add_tracks(self.userid,playlist["id"],[self.trackid])
            
    def remove_track_from_playlist(self):
        self.sp.user_playlist_remove_all_occurrences_of_tracks(self.userid,self.playlistid,[self.trackid])
        xbmc.executebuiltin("Container.Refresh")
        
    def unfollow_playlist(self):
        self.sp.unfollow_playlist(self.ownerid, self.playlistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def follow_artist(self):
        result = self.sp.follow("artist", self.artistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def save_album(self):
        result = self.sp.current_user_saved_albums_add([self.albumid])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def remove_album(self):
        result = self.sp.current_user_saved_albums_delete([self.albumid])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def save_track(self):
        result = self.sp.current_user_saved_tracks_add([self.trackid])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def remove_track(self):
        result = self.sp.current_user_saved_tracks_delete([self.trackid])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def unfollow_artist(self):
        self.sp.unfollow("artist", self.artistid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def follow_user(self):
        result = self.sp.follow("user", self.userid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def unfollow_user(self):
        self.sp.unfollow("user", self.userid)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        xbmc.executebuiltin("Container.Refresh")
        
    def browse_playlists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        if self.filter=="featured":
            playlists = self.sp.featured_playlists(country=self.usercountry,limit=self.limit,offset=self.offset)
            xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', playlists['message'])
            self.add_playlist_listitems(playlists['playlists']['items'])
            self.addNextButton(playlists['playlists']['total'])
        else:
            xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(136))
            playlists = self.sp.user_playlists(self.ownerid,limit=self.limit,offset=self.offset)
            self.add_playlist_listitems(playlists['items'])
            self.addNextButton(playlists['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def browse_newreleases(self):
        xbmcplugin.setContent(int(sys.argv[1]), "albums")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', ADDON.getLocalizedString(11005))
        result = self.sp.new_releases(country=self.usercountry,limit=self.limit,offset=self.offset)
        self.add_album_listitems(result['albums']['items'])
        self.addNextButton(result['albums']['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def add_track_listitems(self,tracks=None,playlistid="",useAlbumOffset=False, fulldetails=True, albumdetails=None):
        listitems = []
        alltrackids = []
        savedtracks = []
        for item in tracks:
            if item.get("track"): 
                item = item["track"]
            if item.get("id"): alltrackids.append(item["id"])      
        if fulldetails: tracks = []
        savedalbums = []
        chunks = getChunks(alltrackids,20)
        for chunk in getChunks(alltrackids,20):
            if fulldetails: tracks += self.sp.tracks(chunk, market=self.usercountry)['tracks']
            savedtracks += self.sp.current_user_saved_tracks_contains(chunk)
        
        for i, track in enumerate(tracks):
            if track.get('track'): track = track['track']
            if albumdetails: track["album"] = albumdetails
            if track.get("images"): thumb = track["images"][0]['url']
            elif track['album'].get("images"): thumb = track['album']["images"][0]['url']
            else: thumb = ""
    
            if track.get('is_playable',False) != True or not track.get('id'):
                url="plugin://plugin.audio.spotify/?action=unavailablemessage"
            elif xbmc.getCondVisibility("System.Platform.Android") and not self.playbackServiceRunning:
                url="plugin://plugin.audio.spotify/?action=play_android&albumid=%s"%(track['album']['id'])
            elif not self.playbackServiceRunning:
                url = track['preview_url']
            else:
                url = "http://%s/track/%s.wav?idx=%s|%s" %(WINDOW.getProperty("Spotify.PlayServer"),track['id'],i,WINDOW.getProperty("Spotify.PlayToken"))

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
                    "genre": " / ".join(track["album"].get("genres",[])),
                    "year": int(track["album"].get("release_date","0").split("-")[0]),
                    "tracknumber": track["track_number"],
                    "album": track['album']["name"],
                    "artist": " / ".join(artists),
                    "rating": str(self.get_track_rating(track["popularity"])),
                    "duration": track["duration_ms"]/1000
                }
            li.setInfo( type="Music", infoLabels=infolabels)
            li.setProperty("spotifytrackid",track['id'])
            contextitems = []
            if savedtracks[i] == True:
                contextitems.append( (ADDON.getLocalizedString(11008),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_track&trackid=%s)"%(track['id'])) )
            else:
                contextitems.append( (ADDON.getLocalizedString(11007),"RunPlugin(plugin://plugin.audio.spotify/?action=save_track&trackid=%s)"%(track['id'])) )
            contextitems.append( (xbmc.getLocalizedString(526),"RunPlugin(plugin://plugin.audio.spotify/?action=add_track_to_playlist&trackid=%s)"%(track['uri'])) )
            if playlistid:
                contextitems.append( (ADDON.getLocalizedString(11017),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_track_from_playlist&trackid=%s&playlistid=%s)"%(track['uri'],playlistid)) )
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s,return)"%item['artists'][0]['id']) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s,return)"%item['artists'][0]['id']) )
            contextitems.append( (ADDON.getLocalizedString(11018),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=browse_artistalbums&artistid=%s,return)"%item['artists'][0]['id']) )
            li.addContextMenuItems(contextitems,True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=False)

    def add_album_listitems(self,albums):
        allalbumids = []
        
        for item in albums:
            if item.get("album"):
                item = item["album"]
            allalbumids.append(item["id"])
        
        #get full info in chunks of 20
        albums = []
        savedalbums = []
        chunks = getChunks(allalbumids,20)
        for chunk in getChunks(allalbumids,20):
            albums += self.sp.albums(chunk, market=self.usercountry)['albums']
            savedalbums += self.sp.current_user_saved_albums_contains(chunk)
                
        #process listing
        for i, item in enumerate(albums):    
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
                
            artists = []
            for artist in item['artists']:
                artists.append(artist["name"])
            
            infolabels = { 
                    "title": item["name"],
                    "genre": " / ".join(item["genres"]),
                    "year": int(item["release_date"].split("-")[0]),
                    "album": item["name"],
                    "artist": " / ".join(artists),
                    "rating": str(self.get_track_rating(item["popularity"]))
                }
            li.setInfo( type="Music", infoLabels=infolabels)
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            contextitems = []
            contextitems.append( (xbmc.getLocalizedString(1024),"RunPlugin(%s)"%url) )
            if savedalbums[i] == True:
                contextitems.append( (ADDON.getLocalizedString(11008),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_album&albumid=%s)"%(item['id'])) )
            else:
                contextitems.append( (ADDON.getLocalizedString(11007),"RunPlugin(plugin://plugin.audio.spotify/?action=save_album&albumid=%s)"%(item['id'])) )
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s,return)"%item['artists'][0]['id']) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s,return)"%item['artists'][0]['id']) )
            contextitems.append( (ADDON.getLocalizedString(11018),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=browse_artistalbums&artistid=%s,return)"%item['artists'][0]['id']) )
            li.addContextMenuItems(contextitems,False)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        
    def add_artist_listitems(self,artists):
        for item in artists:
            if item.get("artist"): 
                item = item["artist"]
            if item.get("images"):
                thumb = item["images"][0]['url']
            else: thumb = ""
            url="plugin://plugin.audio.spotify/?action=browse_artistalbums&artistid=%s"%(item['id'])
            li = xbmcgui.ListItem(
                    item['name'],
                    path=url,
                    iconImage="DefaultMusicArtists.png",
                    thumbnailImage=thumb
                )
            infolabels = { 
                "title": item["name"],
                "genre": " / ".join(item["genres"]),
                "artist": item["name"],
                "rating": str(self.get_track_rating(item["popularity"]))
            }
            li.setInfo( type="Music", infoLabels=infolabels)
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.setLabel2("%s followers" %item["followers"]["total"])
            contextitems = []
            contextitems.append( (xbmc.getLocalizedString(132),"RunPlugin(%s)"%url) )
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s,return)"%(item['id'])) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(MusicLibrary,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s,return)"%(item['id'])) )
            followers = self.sp.following_contains("artist",item['id'])
            if followers[0] == False:
                contextitems.append( (ADDON.getLocalizedString(11009),"RunPlugin(plugin://plugin.audio.spotify/?action=follow_artist&artistid=%s)"%item['id']) )
            else:
                contextitems.append( (ADDON.getLocalizedString(11010),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_artist&artistid=%s)"%item['id']) )
            li.addContextMenuItems(contextitems,True)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)

    def add_playlist_listitems(self,playlists):
        for item in playlists:
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
                if self.filter=="followed" or not self.filter and item['owner']['id'] != self.userid:
                    contextitems.append( (ADDON.getLocalizedString(11010),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                elif item['owner']['id'] != self.userid:
                    followers = self.sp.followers_contains(playlist['owner']['id'],playlist['id'],self.userid)
                    if followers[0] == False:
                        contextitems.append( (ADDON.getLocalizedString(11009),"RunPlugin(plugin://plugin.audio.spotify/?action=follow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                    else:
                        contextitems.append( (ADDON.getLocalizedString(11010),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_playlist&playlistid=%s&ownerid=%s)"%(playlist['id'],playlist['owner']['id'])) )
                li.addContextMenuItems(contextitems,True)
                li.setArt( {"fanart": "special://home/addons/plugin.audio.spotify/fanart.jpg"}  )
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
        
    def browse_artistalbums(self):
        xbmcplugin.setContent(int(sys.argv[1]), "albums")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(132))
        artist = self.sp.artist(self.artistid)
        albums = self.sp.artist_albums(self.artistid,limit=self.limit,offset=self.offset,market=self.usercountry)
        self.add_album_listitems(albums['items'])
        self.addNextButton(albums['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def browse_savedalbums(self):
        xbmcplugin.setContent(int(sys.argv[1]), "albums")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(132))
        albums = self.sp.current_user_saved_albums(limit=self.limit,offset=self.offset)
        self.add_album_listitems(albums['items'])
        self.addNextButton(albums['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def browse_savedtracks(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(134))
        tracks = self.sp.current_user_saved_tracks(limit=self.limit,offset=self.offset,market=self.usercountry)
        self.add_track_listitems(tracks['items'])
        self.addNextButton(tracks['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TRACKNUM)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def browse_savedartists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "artists")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(133))
        #extract the artists from all saved albums
        count = 50
        allartistids = []
        artists = []
        albums = self.sp.current_user_saved_albums(limit=50,offset=0)
        totalitems = albums["total"]
        albums = albums["items"]
        while count < totalitems:
            albums += self.sp.current_user_saved_albums(limit=50,offset=count)["items"]
            count += 50
        for item in albums:
            for artist in item["album"]["artists"]:
                if artist["id"] not in allartistids:
                    allartistids.append(artist["id"])
        for chunk in getChunks(allartistids,50):
            artists += self.sp.artists(chunk)['artists']
        #get all followed artists (hardcoded to 50)
        allfollowedartists = self.sp.current_user_followed_artists(limit=50)['artists']['items']
        for artist in allfollowedartists:
            if not artist["id"] in allartistids:
                artists.append(artist)
        self.add_artist_listitems(artists)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def browse_followedartists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "artists")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(133))
        artists = self.sp.current_user_followed_artists(limit=50) #currently hardcoded to 50
        self.add_artist_listitems(artists['artists']['items'])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def search_artists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "artists")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(133))
        result = self.sp.search(q="artist:%s" %self.artistid, type='artist',limit=self.limit,offset=self.offset,market=self.usercountry)
        self.add_artist_listitems(result['artists']['items'])
        self.addNextButton(result['artists']['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def search_tracks(self):
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(134))
        result = self.sp.search(q="track:%s" %self.trackid, type='track',limit=self.limit,offset=self.offset,market=self.usercountry)
        self.add_track_listitems(result["tracks"]["items"])
        self.addNextButton(result['tracks']['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def search_albums(self):
        xbmcplugin.setContent(int(sys.argv[1]), "albums")
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(132))
        result = self.sp.search(q="album:%s" %self.albumid, type='album',limit=self.limit,offset=self.offset,market=self.usercountry)
        self.add_album_listitems(result['albums']['items'])
        self.addNextButton(result['albums']['total'])
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def search_playlists(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        result = self.sp.search(q="playlist:%s" %self.playlistid, type='playlist',limit=self.limit,offset=self.offset,market=self.usercountry)
        xbmcplugin.setProperty(int(sys.argv[1]),'FolderName', xbmc.getLocalizedString(136))
        self.add_playlist_listitems(result['playlists']['items'])
        self.addNextButton(result['playlists']['total'])
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def search(self):
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        xbmcplugin.setPluginCategory(int(sys.argv[1]), xbmc.getLocalizedString(283))
        kb = xbmc.Keyboard('', xbmc.getLocalizedString(16017))
        kb.doModal()
        if kb.isConfirmed():
            value = kb.getText()
            items = []
            result = self.sp.search(q="%s" %value, type='artist,album,track,playlist',limit=1,market=self.usercountry)
            items.append( ("%s (%s)" %(xbmc.getLocalizedString(133),result["artists"]["total"]),"plugin://plugin.audio.spotify/?action=search_artists&artistid=%s"%(value) ) )
            items.append( ("%s (%s)" %(xbmc.getLocalizedString(136),result["playlists"]["total"]),"plugin://plugin.audio.spotify/?action=search_playlists&playlistid=%s"%(value) ) )
            items.append( ("%s (%s)" %(xbmc.getLocalizedString(132),result["albums"]["total"]),"plugin://plugin.audio.spotify/?action=search_albums&albumid=%s"%(value) ) )
            items.append( ("%s (%s)" %(xbmc.getLocalizedString(134),result["tracks"]["total"]),"plugin://plugin.audio.spotify/?action=search_tracks&trackid=%s"%(value) ) )
            for item in items:
                li = xbmcgui.ListItem(
                        item[0],
                        path=item[1],
                        iconImage="DefaultMusicAlbums.png"
                    )
                li.setProperty('do_not_analyze', 'true')
                li.setProperty('IsPlayable', 'false')
                li.addContextMenuItems([],True)
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item[1], listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            
    def checkLoginDetails(self):
        username = SETTING("username").decode("utf-8")
        password = SETTING("password").decode("utf-8")
        loginSuccess = False
        if not username or not password:
            kb = xbmc.Keyboard('', xbmc.getLocalizedString(1019))
            kb.setHiddenInput(False)
            kb.doModal()
            if kb.isConfirmed():
                username = kb.getText().decode("utf-8")
                #also set password
                kb = xbmc.Keyboard('', xbmc.getLocalizedString(12326))
                kb.setHiddenInput(True)
                kb.doModal()
                if kb.isConfirmed():
                    password = kb.getText().decode("utf-8")
                    SAVESETTING("username",username.encode("utf-8"))
                    SAVESETTING("password",password.encode("utf-8"))
        
        if username and password:
            #wait for background service...
            if not WINDOW.getProperty("Spotify.ServiceReady"):
                #start libspotify background service
                xbmc.executebuiltin('RunScript(plugin.audio.spotify)')
                count = 0
                while not WINDOW.getProperty("Spotify.ServiceReady"):
                    logMsg("waiting for service...",True)
                    if count == 50: 
                        break
                    else:
                        xbmc.sleep(1000)
                        count += 1
            
            #check token for webapi
            self.token = util.prompt_for_user_token(username)
            if not self.token:
                dlg.ok(ADDON_NAME, ADDON.getLocalizedString(11019) + ': ' + error)
                return False
            elif WINDOW.getProperty("Spotify.ServiceReady") == "ready" and self.token:
                return True
            else:
                dlg = xbmcgui.Dialog()
                error = WINDOW.getProperty("Spotify.Lasterror")
                try:
                    error = int(error)
                    errorStr = SpotifyError[int(error)]
                    if error == 6:
                        SAVESETTING("username","")
                        SAVESETTING("password","")
                except: print_exc()
                dlg.ok(ADDON_NAME, ADDON.getLocalizedString(11019) + ': ' + errorStr)
                self.playbackServiceRunning = False
                return True
        return False

    def addNextButton(self,listtotal):
        #adds a next button if needed
        params = self.params
        if xbmc.getCondVisibility("Window.IsActive(MusicLibrary)"):
            if listtotal > self.offset+self.limit:
                params["offset"] = self.offset+self.limit
                url = "plugin://plugin.audio.spotify/"
                for key, value in params.iteritems():
                    if key == "action":
                        url += "?%s=%s"%(key,value[0])
                    elif key == "offset":
                        url += "&%s=%s"%(key,value)
                    else:
                        url += "&%s=%s"%(key,value[0])
                li = xbmcgui.ListItem(
                        xbmc.getLocalizedString(33078),
                        path=url,
                        iconImage="DefaultMusicAlbums.png"
                    )
                li.setProperty('do_not_analyze', 'true')
                li.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=True)
            
    def main(self):
        #parse params
        self.params = urlparse.parse_qs(sys.argv[2][1:].decode("utf-8"))
        action=self.params.get("action",None)
        if action: action = "self." + action[0].lower()
        playlistid=self.params.get("playlistid",None)
        if playlistid: self.playlistid = playlistid[0]
        ownerid=self.params.get("ownerid",None)
        if ownerid: self.ownerid = ownerid[0]
        trackid=self.params.get("trackid",None)
        if trackid: self.trackid = trackid[0]
        albumid=self.params.get("albumid",None)
        if albumid: self.albumid = albumid[0]
        artistid=self.params.get("artistid",None)
        if artistid: self.artistid = artistid[0]
        artistname=self.params.get("artistname",None)
        if artistname: self.artistname = artistname[0]
        offset=self.params.get("offset",None)
        if offset: self.offset = int(offset[0])
        filter=self.params.get("applyfilter",None)
        if filter: self.filter = filter[0]
        
        #always check login details
        if self.checkLoginDetails():
            self.sp = spotipy.Spotify(auth=self.token)
            me = self.sp.me()
            self.userid = me.get("id")
            self.usercountry = me.get("country")
            if action:
                eval(action)()
            else:
                self.browse_main()
        else:
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            
