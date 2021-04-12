#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception, parse_spotify_track, PROXY_PORT, get_playername
import xbmc
import xbmcgui
import urllib.parse
import threading
import _thread


class ConnectPlayer(xbmc.Player):
    '''Simulate a Spotify Connect player with the Kodi player'''
    connect_playing = False  # spotify connect is playing
    connect_local = False  # connect player is this device
    username = None
    __playlist = None
    __exit = False
    __ignore_seek = False
    __sp = None
    __skip_events = False

    def __init__(self, **kwargs):
        self.__sp = kwargs.get("sp")
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self, **kwargs)

    def close(self):
        '''cleanup on exit'''
        del self.__playlist

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.connect_playing and not self.__skip_events and not self.connect_is_paused():
            self.__sp.pause_playback()
            log_msg("Playback paused")
        self.__skip_events = False

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.connect_playing and not self.__skip_events and self.connect_is_paused():
            self.__sp.start_playback()
            log_msg("Playback unpaused")
        self.__skip_events = False

    def onPlayBackEnded(self):
        self.connect_playing = False
        self.connect_local = False
        pass

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        filename = ""
        if self.isPlaying():
            filename = self.getPlayingFile()

        if "localhost:%s" % PROXY_PORT in filename:
            if not self.connect_playing and "connect=true" in filename:
                # we started playback with (remote) connect player
                log_msg("Playback started of Spotify Connect stream")
                self.connect_playing = True
                if "silence" in filename:
                    self.connect_local = False
                else:
                    self.connect_local = True
            if "nexttrack" in filename:
                # next track requested for kodi player
                self.__sp.next_track()
            elif self.connect_playing:
                self.update_playlist()

    def onPlayBackSpeedChanged(self, speed):
        '''Kodi event fired when player is fast forwarding/rewinding'''
        pass

    def onPlayBackSeek(self, seekTime, seekOffset):
        '''Kodi event fired when the user is seeking'''
        if self.__ignore_seek:
            self.__ignore_seek = False
        elif self.connect_playing:
            log_msg("Kodiplayer seekto: %s" % seekTime)
            if self.connect_local:
                self.__ignore_seek = True
            self.__sp.seek_track(seekTime)

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        # event is called after every track 
        # check playlist postition to detect if playback is realy stopped
        if self.connect_playing and self.__playlist.getposition() < 0:
            self.connect_playing = False
            self.connect_local = False
            if not self.connect_is_paused():
                self.__sp.pause_playback()
            log_msg("Playback stopped")

    def update_playlist(self):
        '''Update the playlist: add fake item at the end which allows us to skip'''
        if self.connect_local:
            url = "http://localhost:%s/nexttrack" % PROXY_PORT
        else:
            url = "plugin://plugin.audio.spotify/?action=next_track"
        
        li = xbmcgui.ListItem('...', path=url)
        self.__playlist.add(url, li)
        self.__playlist.add(url, li)

    def start_playback(self, track_id):
        self.__skip_events = True
        self.connect_playing = True
        self.__playlist.clear()
        silenced = False
        if not self.connect_local:
            silenced = True
            
        trackdetails = self.__sp.track(track_id)
        url, li = parse_spotify_track(trackdetails, silenced=silenced)
        self.__playlist.add(url, li)
        self.__ignore_seek = True
        if self.connect_local:
            self.__sp.seek_track(0)  # for now we always start a track at the beginning
        # give small handicap to connect player to prevent next track race condition
        xbmc.sleep(100)
        self.play()

    def update_info(self, force):
        cur_playback = self.__sp.current_playback()
        if cur_playback:
            log_msg("Spotify Connect request received : %s" % cur_playback)
            if  cur_playback["device"]["name"] == get_playername() and (not xbmc.getCondVisibility("Player.Paused") and cur_playback["is_playing"] or force):
                player_title = None
                if self.isPlaying():
                    player_title = self.getMusicInfoTag().getTitle()                
                trackdetails = cur_playback["item"]
                # Set volume level
                if cur_playback['device']['volume_percent'] != 50:
                    xbmc.executebuiltin("SetVolume(%s,true)" % cur_playback['device']['volume_percent'] )   
                if trackdetails is not None and (not player_title or player_title != trackdetails["name"]):
                    log_msg("Next track requested by Spotify Connect player.")
                    self.start_playback(trackdetails["id"])
            elif cur_playback["device"]["name"] == get_playername() and xbmc.getCondVisibility("Player.Paused") and cur_playback["is_playing"]:
                log_msg("Playback resumed from pause requested by Spotify Connect." )
                self.__skip_events = True
                # Set volume level
                if cur_playback['device']['volume_percent'] != 50:
                    xbmc.executebuiltin("SetVolume(%s,true)" % cur_playback['device']['volume_percent'] )   
                log_msg("Start position : %s" % cur_playback['progress_ms'])
                self.play(startpos = cur_playback['progress_ms'])
            elif not xbmc.getCondVisibility("Player.Paused"):
                log_msg("Pause requested by Spotify Connect.")
                self.__skip_events = True
                self.pause()             
        else:
            self.__skip_events = True
            self.stop()
                
    def connect_is_paused(self):
        '''check if connect player currently is paused'''
        cur_playback = self.__sp.current_playback()
        if cur_playback:
            if cur_playback["is_playing"]:
                return False
        return True
