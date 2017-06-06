#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception, parse_spotify_track, PROXY_PORT
import xbmc
import xbmcgui
from urllib import quote_plus

class KodiPlayer(xbmc.Player):
    '''Monitor all player events in Kodi'''
    playlist = None
    trackchanging = False
    exit = False
    connect_playing = False # spotify connect is playing
    connect_local = False # connect player is this device 
    is_busy = False

    def __init__(self, **kwargs):
        self.sp = kwargs.get("sp")
        self.playerid = kwargs.get("playerid")
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self)

    def close(self):
        '''cleanup on exit'''
        exit = True
        del self.playlist

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.connect_playing:
            self.sp.pause_playback()
            log_msg("Playback paused")

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.connect_playing:
            self.sp.start_playback()
            log_msg("Playback unpaused")

    def onPlayBackEnded(self):
        pass

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        # set the connect_playing bool to indicate we are playing spotify connect content
        current_playback = self.sp.current_playback()
        self.connect_local = current_playback["device"]["id"] == self.playerid
        self.connect_playing = current_playback["is_playing"]
        if self.connect_playing:
            self.update_playlist()

    def onPlayBackSpeedChanged(self, speed):
        '''Kodi event fired when player is fast forwarding/rewinding'''
        pass

    def onPlayBackSeek(self, seekTime, seekOffset):
        '''Kodi event fired when the user is seeking'''
        pass

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        if self.connect_playing:
            self.sp.pause_playback()
            log_msg("playback stopped")
        self.connect_playing = False
        self.connect_local = False

    def update_playlist(self):
        '''Update the playlist: add fake item at the end which allows us to skip'''
        li = xbmcgui.ListItem("Spotify Connect")
        li.setMimeType("audio/wave")
        url = "plugin://plugin.audio.spotify/?action=next_track"
        self.playlist.add(url, li)
        self.playlist.add(url, li)
