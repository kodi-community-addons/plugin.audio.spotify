# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
from utils import *
add_external_libraries()
import math
import urlparse
import urllib
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
    limit = 50
    params = {}
    
    appendArtistToTitle = SETTING("appendArtistToTitle") == "true"
    songDefaultView = SETTING("self.songDefaultView")
    artistDefaultView = SETTING("self.artistDefaultView")
    playlistDefaultView = SETTING("self.playlistDefaultView")
    albumDefaultView = SETTING("self.albumDefaultView")
    
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    
    def build_url(self, query):
        query_encoded = {}
        for key, value in query.iteritems():
            query_encoded[try_encode(key)] = try_encode(value)
        return self.base_url + '?' + urllib.urlencode(query_encoded)

    def getListFromCache(self,cacheStr):
        items = []
        if not WINDOW.getProperty("Spotify.IgnoreCache"):
            cacheStr = try_encode(u"SpotifyCache.%s" %cacheStr)
            cache = WINDOW.getProperty(cacheStr).decode("utf-8")
            if cache: items = eval(cache)
        return items
        
    def setListInCache(self,cacheStr,items):
        cacheStr = try_encode(u"SpotifyCache.%s" %cacheStr)
        WINDOW.setProperty(cacheStr, repr(items))
    
    def refresh_listing(self,propstoflush=[]):
        if propstoflush:
            for prop in propstoflush:
                WINDOW.clearProperty("SpotifyCache.%s"%prop)
        WINDOW.setProperty("Spotify.IgnoreCache","ignore1")
        xbmc.executebuiltin("Container.Refresh")
    
    def unavailablemessage(self):
        dlg = xbmcgui.Dialog()
        dlg.ok(ADDON_NAME, ADDON.getLocalizedString(11004))
        xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=False, listitem=xbmcgui.ListItem())
    
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
            
    def play_track(self):
        track = self.sp.track(self.trackid, market=self.usercountry)
        if track.get("images"): 
            thumb = track["images"][0]['url']
        elif track['album'].get("images"): 
            thumb = track['album']["images"][0]['url']
        else: 
            thumb = ""

        if WINDOW.getProperty("Spotify.ServiceReady") == "noplayback":
            url = track['preview_url']
        else:
            url = "http://%s/track/%s.wav?idx=1|%s" %(WINDOW.getProperty("Spotify.PlayServer"),track['id'],WINDOW.getProperty("Spotify.PlayToken"))
        
        artists = []
        for artist in track['artists']:
            artists.append(artist["name"])
        track["artist"] = " / ".join(artists)
        track["genre"] = " / ".join(track["album"].get("genres",[]))
        track["year"] = int(track["album"].get("release_date","0").split("-")[0])
        track["rating"] = str(self.get_track_rating(track["popularity"]))
        
        li = xbmcgui.ListItem(
                track['name'],
                path = url,
                iconImage="DefaultMusicSongs.png",
                thumbnailImage=thumb
            )

        infolabels = { 
                    "title":track['name'],
                    "genre": track["genre"],
                    "year": track["year"],
                    "tracknumber": track["track_number"],
                    "album": track['album']["name"],
                    "artist": track["artist"],
                    "rating": track["rating"],
                    "duration": track["duration_ms"]/1000
                }
        li.setInfo( type="Music", infoLabels=infolabels)
        li.setProperty("spotifytrackid",track['id'])
        if KODI_VERSION > 15:
            li.setContentLookup(False)
        li.setProperty('do_not_analyze', 'true')
        
        xbmcplugin.setResolvedUrl(handle=self.addon_handle, succeeded=True, listitem=li)
        
    def browse_main(self):
        #main listing
        xbmcplugin.setContent(self.addon_handle, "files")
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
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
    
    def browse_main_library(self):
        #library nodes
        xbmcplugin.setContent(self.addon_handle, "files")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', ADDON.getLocalizedString(11013))
        items = []
        items.append( (xbmc.getLocalizedString(136),"plugin://plugin.audio.spotify/?action=browse_playlists&ownerid=%s"%(self.userid),"DefaultMusicPlaylists.png" ) )
        items.append( (xbmc.getLocalizedString(132),"plugin://plugin.audio.spotify/?action=browse_savedalbums","DefaultMusicAlbums.png" ) )
        items.append( (xbmc.getLocalizedString(134),"plugin://plugin.audio.spotify/?action=browse_savedtracks","DefaultMusicSongs.png" ) )
        items.append( (xbmc.getLocalizedString(133),"plugin://plugin.audio.spotify/?action=browse_savedartists","DefaultMusicArtists.png" ) )
        items.append( (ADDON.getLocalizedString(11023),"plugin://plugin.audio.spotify/?action=browse_topartists","DefaultMusicArtists.png" ) )
        items.append( (ADDON.getLocalizedString(11024),"plugin://plugin.audio.spotify/?action=browse_toptracks","DefaultMusicSongs.png" ) )
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
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        
    def browse_topartists(self):
        xbmcplugin.setContent(self.addon_handle, "artists")
        items = self.getListFromCache("topartists")
        if not items:
            result = self.sp.current_user_top_artists(limit=20,offset=0)
            count = len(result["items"])
            while result["total"] > count:
                result["items"] += self.sp.current_user_top_artists(limit=20,offset=count)["items"]
                count += 50
            items = self.prepare_artist_listitems(result["items"])
            self.setListInCache("topartists",items)
        self.add_artist_listitems(items)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.artistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.artistDefaultView)
        
    def browse_toptracks(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        items = self.getListFromCache("toptracks")
        if not items:
            items = self.sp.current_user_top_tracks(limit=20,offset=0)
            count = len(items["items"])
            while items["total"] > count:
                items["items"] += self.sp.current_user_top_tracks(limit=20,offset=count)["items"]
                count += 50
            items = self.prepare_track_listitems(tracks=items["items"])
            self.setListInCache("toptracks",items)
        self.add_track_listitems(items,True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.songDefaultView:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)

    def get_explore_categories(self):
        items = self.getListFromCache("explore_categories")
        if not items:
            categories = self.sp.categories(country=self.usercountry,limit=50,locale=self.usercountry)
            count = len(categories["categories"]["items"])
            while categories["categories"]["total"] > count:
                categories["categories"]["items"] += self.sp.categories(country=self.usercountry,limit=50,offset=count,locale=self.usercountry)["categories"]["items"]
                count += 50
            for item in categories["categories"]["items"]:
                thumb = "DefaultMusicGenre.png"
                for icon in item["icons"]:
                    thumb = icon["url"]
                    break
                items.append( (item["name"],"plugin://plugin.audio.spotify/?action=browse_category&applyfilter=%s"%(item["id"]),thumb ) )
            self.setListInCache("explore_categories",items)
        return items
    
    def browse_main_explore(self):
        #explore nodes
        xbmcplugin.setContent(self.addon_handle, "files")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', ADDON.getLocalizedString(11014))
        items = []
        items.append( (ADDON.getLocalizedString(11015),"plugin://plugin.audio.spotify/?action=browse_playlists&applyfilter=featured","DefaultMusicPlaylists.png" ) )
        items.append( (ADDON.getLocalizedString(11016),"plugin://plugin.audio.spotify/?action=browse_newreleases","DefaultMusicAlbums.png" ) )
        
        #add categories
        items += self.get_explore_categories()
        
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
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item[1], listitem=li, isFolder=True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
    
    def getAllAlbumTracks(self,album):
        count = 0
        cacheStr = "getAllAlbumTracks-%s" %album["id"]
        alltracks = self.getListFromCache(cacheStr)
        if not alltracks:
            trackids = []
            while album["tracks"]["total"] > count:
                albumtracks = self.sp.album_tracks(album["id"],market=self.usercountry,limit=50,offset=count)["items"]
                for track in albumtracks:
                    trackids.append(track["id"])
                count += 50
            alltracks = self.prepare_track_listitems(trackids,albumdetails=album) 
            self.setListInCache(cacheStr,alltracks)
        return alltracks
        
    def browse_album(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        album = self.sp.album(self.albumid,market=self.usercountry)
        xbmcplugin.setProperty(self.addon_handle,'FolderName', album["name"])
        tracks = self.getAllAlbumTracks(album)
        if album.get("album_type") == "compilation":
            self.add_track_listitems(tracks,True)
        else: self.add_track_listitems(tracks)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_ARTIST)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.songDefaultView:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)
     
    def artist_toptracks(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', ADDON.getLocalizedString(11011))
        cacheStr = "artisttoptracks.%s" %self.artistid
        tracks = self.getListFromCache(cacheStr)
        if not tracks:
            tracks = self.sp.artist_top_tracks(self.artistid,country=self.usercountry)
            tracks = self.prepare_track_listitems(tracks=tracks["tracks"])
            self.setListInCache(cacheStr,tracks)
        self.add_track_listitems(tracks)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.songDefaultView:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)
    
    def related_artists(self):
        xbmcplugin.setContent(self.addon_handle, "artists")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', ADDON.getLocalizedString(11012))
        cacheStr = "relatedartists.%s" %self.artistid
        artists = self.getListFromCache(cacheStr)
        if not artists:
            artists = self.sp.artist_related_artists(self.artistid)
            artists = self.prepare_artist_listitems(artists['artists'])
            self.setListInCache(cacheStr,artists)
        self.add_artist_listitems(artists)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.artistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.artistDefaultView)
    
    def get_playlist(self, ownerid, playlistid):
        playlist = self.sp.user_playlist(ownerid, playlistid,market=self.usercountry, fields="tracks(total),name,owner(id),id")
        #get from cache first
        cacheStr = "getAllPlaylistTracks-%s-%s" %(playlist["id"],playlist["tracks"]["total"])
        playlistdetails = self.getListFromCache(cacheStr)
        if not playlistdetails:
            #get listing from api
            count = 0
            playlistdetails = playlist
            playlistdetails["tracks"]["items"] = []
            while playlist["tracks"]["total"] > count:
                playlistdetails["tracks"]["items"] += self.sp.user_playlist_tracks(playlist["owner"]["id"], playlist["id"],market=self.usercountry,fields="",limit=50,offset=count)["items"]
                count += 50
            trackids = []
            playlistdetails["tracks"]["items"] = self.prepare_track_listitems(tracks=playlistdetails["tracks"]["items"],playlistdetails=playlist)
            self.setListInCache(cacheStr,playlistdetails)
        return playlistdetails
    
    def browse_playlist(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        playlistdetails = self.get_playlist(self.ownerid,self.playlistid)
        xbmcplugin.setProperty(self.addon_handle,'FolderName', playlistdetails["name"])
        self.add_track_listitems(playlistdetails["tracks"]["items"],True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.songDefaultView:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)
    
    def get_category(self,categoryid):
        cachestr = "browse_category.%s" %categoryid
        playlists = self.getListFromCache(cachestr)
        if not playlists:
            category = self.sp.category(categoryid,country=self.usercountry,locale=self.usercountry)
            playlists = self.sp.category_playlists(categoryid,country=self.usercountry,limit=50,offset=0)
            playlists['category'] = category["name"]
            count = len(playlists['playlists']['items'])
            while playlists['playlists']['total'] > count:
                playlists['playlists']['items'] += self.sp.category_playlists(categoryid,country=self.usercountry,limit=50,offset=count)['playlists']['items']
                count += 50
            playlists['playlists']['items'] = self.prepare_playlist_listitems(playlists['playlists']['items'])
            self.setListInCache(cachestr,playlists)
        return playlists
    
    def browse_category(self):
        xbmcplugin.setContent(self.addon_handle, "files")
        playlists = self.get_category(self.filter)
        self.add_playlist_listitems(playlists['playlists']['items'])
        xbmcplugin.setProperty(self.addon_handle,'FolderName', playlists['category'])
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        
    def follow_playlist(self):
        result = self.sp.follow_playlist(self.ownerid, self.playlistid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing()
        
    def add_track_to_playlist(self):
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        
        if not self.trackid and xbmc.getInfoLabel("MusicPlayer.(1).Property(spotifytrackid)"):
            self.trackid = xbmc.getInfoLabel("MusicPlayer.(1).Property(spotifytrackid)")
        
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
        self.refresh_listing()
        
    def unfollow_playlist(self):
        self.sp.unfollow_playlist(self.ownerid, self.playlistid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing()
        
    def follow_artist(self):
        result = self.sp.follow("artist", self.artistid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["followed_artists","savedartists"])
    
    def unfollow_artist(self):
        self.sp.unfollow("artist", self.artistid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["followed_artists","savedartists"])
        
    def save_album(self):
        result = self.sp.current_user_saved_albums_add([self.albumid])
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["savedalbums","savedartists","savedalbumsids"])
        
    def remove_album(self):
        result = self.sp.current_user_saved_albums_delete([self.albumid])
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["savedalbums","savedartists","savedalbumsids"])
        
    def save_track(self):
        result = self.sp.current_user_saved_tracks_add([self.trackid])
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["usersavedtracks","usersavedtracksids"])
        
    def remove_track(self):
        result = self.sp.current_user_saved_tracks_delete([self.trackid])
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing(["usersavedtracks","usersavedtracksids"])
        
    def follow_user(self):
        result = self.sp.follow("user", self.userid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing()
        
    def unfollow_user(self):
        self.sp.unfollow("user", self.userid)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        self.refresh_listing()
        
    def get_featured_playlists(self):
        playlists = self.getListFromCache("featuredplaylists")
        if not playlists:
            playlists = self.sp.featured_playlists(country=self.usercountry,limit=50,offset=0)
            count = len(playlists['playlists']['items'])
            total = playlists['playlists']['total']
            while total > count:
                playlists['playlists']['items'] += self.sp.featured_playlists(country=self.usercountry,limit=50,offset=count)['playlists']['items']
                count += 50
            playlists['playlists']['items'] = self.prepare_playlist_listitems(playlists['playlists']['items'])
            self.setListInCache("featuredplaylists",playlists)
        return playlists
        
    def get_user_playlists(self,userid):
        playlists = self.sp.user_playlists(userid,limit=1,offset=0)
        count = len(playlists['items'])
        total = playlists['total']
        cacheStr = "userplaylists.%s.%s" %(userid,total)
        cache = self.getListFromCache(cacheStr)
        if cache: 
            playlists = cache
        else:
            while total > count:
                playlists["items"] += self.sp.user_playlists(userid,limit=50,offset=count)["items"]
                count += 50
            playlists = self.prepare_playlist_listitems(playlists['items'])
            self.setListInCache(cacheStr,playlists)
        return playlists
    
    def get_curuser_playlistids(self):
        playlistids = []
        playlists = self.sp.current_user_playlists(limit=1,offset=0)
        count = len(playlists['items'])
        total = playlists['total']
        cacheStr = "userplaylistids.%s" %total
        playlistids = self.getListFromCache(cacheStr)
        if not playlistids: 
            while total > count:
                playlists["items"] += self.sp.current_user_playlists(limit=50,offset=count)["items"]
                count += 50
            for playlist in playlists["items"]:
                playlistids.append(playlist["id"])
            self.setListInCache(cacheStr,playlistids)
        return playlistids

    def browse_playlists(self):
        xbmcplugin.setContent(self.addon_handle, "files")
        if self.filter=="featured":
            playlists = self.get_featured_playlists()
            xbmcplugin.setProperty(self.addon_handle,'FolderName', playlists['message'])
            playlists = playlists['playlists']['items']
        else:
            xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(136))
            playlists = self.get_user_playlists(self.ownerid)
        
        self.add_playlist_listitems(playlists)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.playlistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.playlistDefaultView)
    
    def get_newreleases(self):
        albums = self.getListFromCache("newreleases")
        if not albums:
            albums = self.sp.new_releases(country=self.usercountry,limit=50,offset=0)
            count = len(albums['albums']['items'])
            while albums["albums"]["total"] > count:
                albums['albums']['items'] += self.sp.new_releases(country=self.usercountry,limit=50,offset=count)['albums']['items']
                count += 50
            albumids = []
            for album in albums['albums']['items']:
                albumids.append(album["id"])
            albums = self.prepare_album_listitems(albumids)
            self.setListInCache("newreleases",albums)
        return albums
    
    def browse_newreleases(self):
        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', ADDON.getLocalizedString(11005))
        albums = self.get_newreleases()
        self.add_album_listitems(albums)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.albumDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.albumDefaultView)
    
    def prepare_track_listitems(self, trackids=[], tracks=[], playlistdetails=None, albumdetails=None):
        newtracks = []
        #for tracks we always get the full details unless full tracks already supplied
        if trackids and not tracks:
            chunks = getChunks(trackids,20)
            for chunk in getChunks(trackids,20):
                tracks += self.sp.tracks(chunk, market=self.usercountry)['tracks']
        
        savedtracks = self.get_saved_tracks_ids()
        
        followedartists = []
        for artist in self.get_followedartists():
            followedartists.append(artist["id"])
            
        for track in tracks:
            
            if track.get('track'): track = track['track']
            if albumdetails: track["album"] = albumdetails
            if track.get("images"): thumb = track["images"][0]['url']
            elif track['album'].get("images"): thumb = track['album']["images"][0]['url']
            else: thumb = ""
            track['thumb'] = thumb
            
            #skip local tracks in playlists
            if not track['id']: continue
    
            if WINDOW.getProperty("Spotify.ServiceReady") == "noplayback":
                track["url"] = track['preview_url']
            else:
                track["url"] = "http://%s/track/%s.wav?idx=1|%s" %(WINDOW.getProperty("Spotify.PlayServer"),track['id'],WINDOW.getProperty("Spotify.PlayToken"))

            artists = []
            for artist in track['artists']:
                artists.append(artist["name"])
            track["artist"] = " / ".join(artists)
            track["genre"] = " / ".join(track["album"].get("genres",[]))
            track["year"] = int(track["album"].get("release_date","0").split("-")[0])
            track["rating"] = str(self.get_track_rating(track["popularity"]))
            if playlistdetails:
                track["playlistid"] = playlistdetails["id"]
            track["artistid"] = track['artists'][0]['id']
            
            #use original trackid for actions when the track was relinked
            if track.get("linked_from"):
                real_trackid = track["linked_from"]["id"]
                real_trackuri = track["linked_from"]["uri"]
            else:
                real_trackid = track["id"]
                real_trackuri = track["uri"]
            
            contextitems = []
            if track["id"] in savedtracks:
                contextitems.append( (ADDON.getLocalizedString(11008),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_track&trackid=%s)"%(real_trackid)) )
            else:
                contextitems.append( (ADDON.getLocalizedString(11007),"RunPlugin(plugin://plugin.audio.spotify/?action=save_track&trackid=%s)"%(real_trackid)) )
            
            if playlistdetails and playlistdetails["owner"]["id"] == self.userid:
                contextitems.append( (ADDON.getLocalizedString(11017),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_track_from_playlist&trackid=%s&playlistid=%s)"%(real_trackuri,playlistdetails["id"])) )
            elif not playlistdetails:
                contextitems.append( (xbmc.getLocalizedString(526),"RunPlugin(plugin://plugin.audio.spotify/?action=add_track_to_playlist&trackid=%s)"%real_trackuri) )
            
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s)"%track["artistid"]) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s)"%track["artistid"]) )
            contextitems.append( (ADDON.getLocalizedString(11018),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=browse_artistalbums&artistid=%s)"%track["artistid"]) )
            
            if track["artistid"] in followedartists:
                #unfollow artist
                contextitems.append( (ADDON.getLocalizedString(11026),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_artist&artistid=%s)"%track["artistid"]) )
            else:
                #follow artist
                contextitems.append( (ADDON.getLocalizedString(11025),"RunPlugin(plugin://plugin.audio.spotify/?action=follow_artist&artistid=%s)"%track["artistid"]) )
            
            contextitems.append( (ADDON.getLocalizedString(11027),"RunPlugin(plugin://plugin.audio.spotify/?action=refresh_listing)") )
            track["contextitems"] = contextitems
            newtracks.append(track)
            
        return newtracks
            
    def add_track_listitems(self,tracks,appendArtistToLabel=False):
        list_items = []
        for track in tracks:
        
            if appendArtistToLabel:
                label = "%s - %s" %(track["artist"],track['name'])
            else:
                label = track['name']
                
            li = xbmcgui.ListItem(
                    label,
                    path=track['url'],
                    iconImage="DefaultMusicSongs.png",
                    thumbnailImage=track['thumb']
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'true')
            
            if self.appendArtistToTitle:
                title = label
            else:
                title = track['name']

            li.setInfo( 'music', { 
                    "title":title,
                    "genre": track["genre"],
                    "year": track["year"],
                    "tracknumber": track["track_number"],
                    "album": track['album']["name"],
                    "artist": track["artist"],
                    "rating": track["rating"],
                    "duration": track["duration_ms"]/1000
                })
            li.setProperty("spotifytrackid",track['id'])
            if KODI_VERSION > 15:
                li.setContentLookup(False)
            li.addContextMenuItems(track["contextitems"])
            list_items.append((track["url"], li, False))
        xbmcplugin.addDirectoryItems(self.addon_handle, list_items)
    
    def prepare_album_listitems(self, albumids=[], albums=[]):
        
        if not albums and albumids:
            #get full info in chunks of 20
            chunks = getChunks(albumids,20)
            for chunk in getChunks(albumids,20):
                albums += self.sp.albums(chunk, market=self.usercountry)['albums']
        
        savedalbums = self.get_savedalbumsids()
                
        #process listing
        for item in albums:    
            if item.get("images"):
                item['thumb'] = item["images"][0]['url']
            else: item['thumb'] = ""
            
            item['url'] = self.build_url({'action': 'browse_album', 'albumid': item['id'] })
            
            artists = []
            for artist in item['artists']:
                artists.append(artist["name"])
            item['artist'] = " / ".join(artists)
            item["genre"] = " / ".join(item["genres"])
            item["year"] = int(item["release_date"].split("-")[0])
            item["rating"] = str(self.get_track_rating(item["popularity"]))
            item["artistid"] = item['artists'][0]['id']
            
            contextitems = []
            contextitems.append( (xbmc.getLocalizedString(1024),"RunPlugin(%s)"%item["url"]) )
            if item["id"] in savedalbums:
                contextitems.append( (ADDON.getLocalizedString(11008),"RunPlugin(plugin://plugin.audio.spotify/?action=remove_album&albumid=%s)"%(item['id'])) )
            else:
                contextitems.append( (ADDON.getLocalizedString(11007),"RunPlugin(plugin://plugin.audio.spotify/?action=save_album&albumid=%s)"%(item['id'])) )
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s)"%item["artistid"]) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s)"%item["artistid"]) )
            contextitems.append( (ADDON.getLocalizedString(11018),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=browse_artistalbums&artistid=%s)"%item["artistid"]) )
            contextitems.append( (ADDON.getLocalizedString(11027),"RunPlugin(plugin://plugin.audio.spotify/?action=refresh_listing)") )
            item["contextitems"] = contextitems
        return albums
        
    def add_album_listitems(self,albums,appendArtistToLabel=False):
  
        #process listing
        for item in albums:
            
            if appendArtistToLabel:
                label = "%s - %s" %(item["artist"],item['name'])
            else:
                label = item['name']
                
            li = xbmcgui.ListItem(
                    label,
                    path=item['url'],
                    iconImage="DefaultMusicAlbums.png",
                    thumbnailImage=item['thumb']
                )

            infolabels = { 
                    "title": item['name'],
                    "genre": item["genre"],
                    "year": item["year"],
                    "album": item["name"],
                    "artist": item["artist"],
                    "rating": item["rating"]
                }
            li.setInfo( type="Music", infoLabels=infolabels)
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.addContextMenuItems(item["contextitems"],False)
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item["url"], listitem=li, isFolder=True)
        
    def prepare_artist_listitems(self,artists,isFollowed=False):
        
        followedartists = []
        if not isFollowed:
            for artist in self.get_followedartists():
                followedartists.append(artist["id"])
                
        for item in artists:
            if not item: 
                return []
            if item.get("artist"): 
                item = item["artist"]
            if item.get("images"):
                item["thumb"] = item["images"][0]['url']
            else: item["thumb"] = ""
            
            item['url'] = self.build_url({'action': 'browse_artistalbums', 'artistid': item['id'] })
            
            item["genre"] = " / ".join(item["genres"])
            item["rating"] = str(self.get_track_rating(item["popularity"]))
            item["followerslabel"] = "%s followers" %item["followers"]["total"]
            contextitems = []
            contextitems.append( (xbmc.getLocalizedString(132),"ActivateWindow(Music,%s)"%item["url"]) )
            contextitems.append( (ADDON.getLocalizedString(11011),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=artist_toptracks&artistid=%s)"%(item['id'])) )
            contextitems.append( (ADDON.getLocalizedString(11012),"ActivateWindow(Music,plugin://plugin.audio.spotify/?action=related_artists&artistid=%s)"%(item['id'])) )
            if isFollowed or item["id"] in followedartists:
                #unfollow artist
                contextitems.append( (ADDON.getLocalizedString(11026),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_artist&artistid=%s)"%item['id']) )
            else:
                #follow artist
                contextitems.append( (ADDON.getLocalizedString(11025),"RunPlugin(plugin://plugin.audio.spotify/?action=follow_artist&artistid=%s)"%item['id']) )
            item["contextitems"] = contextitems
        return artists
            
    def add_artist_listitems(self,artists):
        for item in artists:
            li = xbmcgui.ListItem(
                    item['name'],
                    path=item["url"],
                    iconImage="DefaultMusicArtists.png",
                    thumbnailImage=item["thumb"]
                )
            infolabels = { 
                "title": item["name"],
                "genre": item["genre"],
                "artist": item["name"],
                "rating": item["rating"]
            }
            li.setInfo( type="Music", infoLabels=infolabels)
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            li.setLabel2(item["followerslabel"])
            li.addContextMenuItems(item["contextitems"])
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item["url"], listitem=li, isFolder=True, totalItems=len(artists))

    def prepare_playlist_listitems(self,playlists):
        playlists2 = []
        followed_playlists = self.get_curuser_playlistids()
        for item in playlists:

            if item.get("images"):
                item["thumb"] = item["images"][0]['url']
            else: item["thumb"] = ""
            
            item['url'] = self.build_url({'action': 'browse_playlist', 'playlistid': item['id'], 'ownerid': item['owner']['id'] })

            contextitems = []
            if item['owner']['id'] != self.userid and item['id'] in followed_playlists:
                #unfollow playlist
                contextitems.append( (ADDON.getLocalizedString(11010),"RunPlugin(plugin://plugin.audio.spotify/?action=unfollow_playlist&playlistid=%s&ownerid=%s)"%(item['id'],item['owner']['id'])) )
            elif item['owner']['id'] != self.userid:
                #follow playlist
                contextitems.append( (ADDON.getLocalizedString(11009),"RunPlugin(plugin://plugin.audio.spotify/?action=follow_playlist&playlistid=%s&ownerid=%s)"%(item['id'],item['owner']['id'])) )
            contextitems.append( (ADDON.getLocalizedString(11027),"RunPlugin(plugin://plugin.audio.spotify/?action=refresh_listing)") )
            item["contextitems"] = contextitems
            playlists2.append(item)
        return playlists2
        
    def add_playlist_listitems(self,playlists):
        
        for item in playlists:
            
            li = xbmcgui.ListItem(
                    item['name'],
                    path=item["url"],
                    iconImage="DefaultMusicAlbums.png",
                    thumbnailImage=item["thumb"]
                )
            li.setProperty('do_not_analyze', 'true')
            li.setProperty('IsPlayable', 'false')
            
            li.addContextMenuItems(item["contextitems"])
            li.setArt( {"fanart": "special://home/addons/plugin.audio.spotify/fanart.jpg"}  )
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item["url"], listitem=li, isFolder=True)
        
    def browse_artistalbums(self):
        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(132))
        cachestr = "artistalbums.%s" %self.artistid
        albums = self.getListFromCache(cachestr)
        if not albums:
            artist = self.sp.artist(self.artistid)
            artistalbums = self.sp.artist_albums(self.artistid,limit=50,offset=0,market=self.usercountry,album_type='album,single,compilation')
            count = len(artistalbums['items'])
            albumids = []
            while artistalbums['total'] > count:
                artistalbums['items'] += self.sp.artist_albums(self.artistid,limit=50,offset=count,market=self.usercountry,album_type='album,single,compilation' )['items']
                count += 50
            for album in artistalbums['items']:
                albumids.append(album["id"])
            albums = self.prepare_album_listitems(albumids)
            self.setListInCache(cachestr,albums)
        self.add_album_listitems(albums)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.albumDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.albumDefaultView)
    
    def get_savedalbumsids(self):
        albumids = self.getListFromCache("savedalbumsids")
        if not albumids:
            albums = self.sp.current_user_saved_albums(limit=50,offset=0)
            count = len(albums["items"])
            while albums["total"] > count:
                albums["items"] += self.sp.current_user_saved_albums(limit=50,offset=count)["items"]
                count += 50
            for album in albums["items"]:
                albumids.append(album["album"]["id"])
            self.setListInCache("savedalbumsids",albumids)
        return albumids
    
    def get_savedalbums(self):
        albums = self.getListFromCache("savedalbums")
        if not albums:
            albumids = self.get_savedalbumsids()
            albums = self.prepare_album_listitems(albumids)
            self.setListInCache("savedalbums",albums)
        return albums
    
    def browse_savedalbums(self):
        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(132))
        albums = self.get_savedalbums()
        self.add_album_listitems(albums,True)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        xbmcplugin.setContent(self.addon_handle, "albums")
        if self.albumDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.albumDefaultView)
    
    def get_saved_tracks_ids(self):
        trackids = self.getListFromCache("usersavedtracksids")
        if not trackids:
            #get from api
            saved_tracks = self.sp.current_user_saved_tracks(limit=self.limit,offset=self.offset,market=self.usercountry)
            count = len(saved_tracks["items"])
            total = saved_tracks["total"]
            while total > count:
                saved_tracks["items"] += self.sp.current_user_saved_tracks(limit=50,offset=count,market=self.usercountry)["items"]
                count += 50
            for track in saved_tracks["items"]:
                trackids.append(track["track"]["id"])
            self.setListInCache("usersavedtracksids",trackids)
        return trackids
                       
    def get_saved_tracks(self):
        #get from cache first
        tracks = self.getListFromCache("usersavedtracks")
        if not tracks:
            #get from api
            trackids = self.get_saved_tracks_ids()
            tracks = self.prepare_track_listitems(trackids)
            self.setListInCache("usersavedtracks",tracks)
        return tracks
    
    def browse_savedtracks(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        #xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(134))
        tracks = self.get_saved_tracks()
        self.add_track_listitems(tracks,True)
        # xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        # xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
        # xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TITLE)
        # xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        # xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_SONG_RATING)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        # if self.songDefaultView:
            # xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)
    
    def get_savedartists(self):
        artists = self.getListFromCache("savedartists")
        if not artists:
            #extract the artists from all saved albums
            albums = self.get_savedalbums()
            allartistids = []
            artists = []
            for item in albums:
                for artist in item["artists"]:
                    if artist["id"] not in allartistids:
                        allartistids.append(artist["id"])
            for chunk in getChunks(allartistids,50):
                artists += self.prepare_artist_listitems(self.sp.artists(chunk)['artists'])
            #get all followed artists
            allfollowedartists = self.get_followedartists()
            for artist in allfollowedartists:
                if not artist["id"] in allartistids:
                    artists.append(artist)
            self.setListInCache("savedartists",artists)
        return artists
    
    def browse_savedartists(self):
        xbmcplugin.setContent(self.addon_handle, "artists")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(133))
        artists = self.get_savedartists()
        self.add_artist_listitems(artists)
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.artistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.artistDefaultView)
    
    def get_followedartists(self):
        artists = self.getListFromCache("followed_artists")
        if not artists:
            artists = self.sp.current_user_followed_artists(limit=50)
            count = len(artists['artists']['items'])
            after = artists['artists']['cursors']['after']
            while artists['artists']['total'] > count:
                result = self.sp.current_user_followed_artists(limit=50, after=after)
                artists['artists']['items'] += result['artists']['items']
                after = result['artists']['cursors']['after']
                count += 50
            artists = self.prepare_artist_listitems(artists['artists']['items'],isFollowed=True)
            self.setListInCache("followed_artists",artists)
        return artists
    
    def browse_followedartists(self):
        xbmcplugin.setContent(self.addon_handle, "artists")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(133))
        artists = self.get_followedartists()
        self.add_artist_listitems(artists)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.artistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.artistDefaultView)
    
    def search_artists(self):
        xbmcplugin.setContent(self.addon_handle, "artists")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(133))
        result = self.sp.search(q="artist:%s" %self.artistid, type='artist',limit=self.limit,offset=self.offset,market=self.usercountry)
        artists = self.prepare_artist_listitems(result['artists']['items'])
        self.add_artist_listitems(artists)
        self.addNextButton(result['artists']['total'])
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.artistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.artistDefaultView)
        
    def search_tracks(self):
        xbmcplugin.setContent(self.addon_handle, "songs")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(134))
        result = self.sp.search(q="track:%s" %self.trackid, type='track',limit=self.limit,offset=self.offset,market=self.usercountry)
        tracks = self.prepare_track_listitems(tracks=result["tracks"]["items"])
        self.add_track_listitems(tracks,True)
        self.addNextButton(result['tracks']['total'])
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.songDefaultView:
            xbmc.executebuiltin('Container.SetViewMode(%s)' %self.songDefaultView)
        
    def search_albums(self):
        xbmcplugin.setContent(self.addon_handle, "albums")
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(132))
        result = self.sp.search(q="album:%s" %self.albumid, type='album',limit=self.limit,offset=self.offset,market=self.usercountry)
        albumids = []
        for album in result['albums']['items']:
            albumids.append(album["id"])
        albums = self.prepare_album_listitems(albumids)
        self.add_album_listitems(albums,True)
        self.addNextButton(result['albums']['total'])
        xbmcplugin.addSortMethod(self.addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.albumDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.albumDefaultView)
        
    def search_playlists(self):
        xbmcplugin.setContent(self.addon_handle, "files")
        result = self.sp.search(q="playlist:%s" %self.playlistid, type='playlist',limit=self.limit,offset=self.offset,market=self.usercountry)
        xbmcplugin.setProperty(self.addon_handle,'FolderName', xbmc.getLocalizedString(136))
        playlists = self.prepare_playlist_listitems(result['playlists']['items'])
        self.add_playlist_listitems(playlists)
        self.addNextButton(result['playlists']['total'])
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
        if self.playlistDefaultView: xbmc.executebuiltin('Container.SetViewMode(%s)' %self.playlistDefaultView)
        
    def search(self):
        xbmcplugin.setContent(self.addon_handle, "files")
        xbmcplugin.setPluginCategory(self.addon_handle, xbmc.getLocalizedString(283))
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
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=item[1], listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(handle=self.addon_handle)
            
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
            error = WINDOW.getProperty("Spotify.Lasterror")
            if not self.token:
                xbmcgui.Dialog().ok(ADDON_NAME, ADDON.getLocalizedString(11019) + ': ' + error)
                return False
            elif WINDOW.getProperty("Spotify.ServiceReady") == "ready" and self.token:
                return True
            elif WINDOW.getProperty("Spotify.ServiceReady") == "noplayback" and self.token:
                return True
            else:
                errorStr = error
                try:
                    error = int(error)
                    errorStr = SpotifyError[int(error)]
                    if error == 6:
                        SAVESETTING("username","")
                        SAVESETTING("password","")
                    elif error == 999:
                        xbmcgui.Dialog().ok(ADDON_NAME, ADDON.getLocalizedString(11019) + ': ' + errorStr)
                        WINDOW.setProperty("Spotify.ServiceReady","noplayback")
                        return True
                except: pass
                xbmcgui.Dialog().ok(ADDON_NAME, ADDON.getLocalizedString(11019) + ': ' + errorStr)
                return False
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
                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)
            
    def main(self):
        #parse params
        self.params = urlparse.parse_qs(sys.argv[2][1:])
        action=self.params.get("action",None)
        if action: action = "self." + action[0].lower().decode("utf-8")
        playlistid=self.params.get("playlistid",None)
        if playlistid: self.playlistid = playlistid[0].decode("utf-8")
        ownerid=self.params.get("ownerid",None)
        if ownerid: self.ownerid = ownerid[0].decode("utf-8")
        trackid=self.params.get("trackid",None)
        if trackid: self.trackid = trackid[0].decode("utf-8")
        albumid=self.params.get("albumid",None)
        if albumid: self.albumid = albumid[0].decode("utf-8")
        artistid=self.params.get("artistid",None)
        if artistid: self.artistid = artistid[0].decode("utf-8")
        artistname=self.params.get("artistname",None)
        if artistname: self.artistname = artistname[0].decode("utf-8")
        offset=self.params.get("offset",None)
        if offset: self.offset = int(offset[0])
        filter=self.params.get("applyfilter",None)
        if filter: self.filter = filter[0].decode("utf-8")
        
        #always check login details
        if self.checkLoginDetails():
            self.sp = spotipy.Spotify(auth=self.token)
            me = self.sp.me()
            self.userid = me["id"]
            self.usercountry = me["country"]
            if action:
                eval(action)()
            else:
                self.browse_main()
                self.precacheAllitems()
        else:
            xbmcplugin.endOfDirectory(handle=self.addon_handle)
        
        if WINDOW.getProperty("Spotify.IgnoreCache") == "ignore1":
            WINDOW.setProperty("Spotify.IgnoreCache","ignore2")
        else:
            WINDOW.clearProperty("Spotify.IgnoreCache")
            
    def precacheAllitems(self):
        if not WINDOW.getProperty("Spotify.PreCachedItems"):
            WINDOW.setProperty("Spotify.PreCachedItems","busy")
            userplaylists = self.get_user_playlists(self.userid)
            for playlist in userplaylists:
                self.get_playlist(playlist['owner']['id'],playlist["id"])
            categories = self.get_explore_categories()
            for category in categories:
                self.get_category(category[1].split("applyfilter=")[-1])
            self.get_savedalbums()
            self.get_savedartists()
            self.get_saved_tracks()
            self.get_newreleases()
            self.get_featured_playlists()
            WINDOW.setProperty("Spotify.PreCachedItems","done")
            
        
        
        