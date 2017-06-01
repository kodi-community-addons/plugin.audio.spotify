#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception, get_playername, parse_spotify_track, PROXY_PORT
import xbmc
import xbmcgui
from urllib import quote_plus

class KodiPlayer(xbmc.Player):
    '''Monitor all player events in Kodi'''
    playlist = None
    trackchanging = False
    exit = False
    is_playing = False
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
        if self.is_playing:
            self.sp.pause_playback()
            log_msg("Playback paused")

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.is_playing:
            self.sp.start_playback()
            log_msg("Playback unpaused")

    def onPlayBackEnded(self):
        pass

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        # set the is_playing bool to indicate we are playing spotify connect content
        current_playback = self.sp.current_playback()
        self.is_playing = current_playback["device"]["id"] == self.playerid and current_playback["is_playing"]          

    def onPlayBackSpeedChanged(self, speed):
        '''Kodi event fired when player is fast forwarding/rewinding'''
        pass

    def onPlayBackSeek(self, seekTime, seekOffset):
        '''Kodi event fired when the user is seeking'''
        pass

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        if self.is_playing:
            self.sp.pause_playback()
            log_msg("playback stopped")
        self.is_playing = False

    def update_playlist(self, trackdetails=None):
        '''Update the playlist'''
        if not trackdetails:
            trackdetails = self.sp.current_playback()["item"]
        self.playlist.clear()
        url, li = parse_spotify_track(trackdetails)
        self.playlist.add(url, li)
        
        li = xbmcgui.ListItem("Spotify Connect")
        li.setInfo('music',
                     {
                         'title': "Spotify Connect",
                         'duration': 10
                     })
        url = "http://127.0.0.1:%s/loadtrack" % PROXY_PORT
        self.playlist.add(url, li)
        
        self.play(self.playlist, startpos=0)

    def wait_for_player(self):
        count = 0
        xbmc.sleep(500)
        while not xbmc.getCondVisibility("Player.HasAudio") and count < 10:
            xbmc.sleep(250)
            count += 1
