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
    is_paused = False
    ignore_seek = False

    def __init__(self, **kwargs):
        self.__sp = kwargs.get("sp")
        self.__direct_playback = kwargs.get("direct_playback")
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self, **kwargs)

    def close(self):
        '''cleanup on exit'''
        exit = True
        del self.__playlist

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.connect_playing and not self.is_paused:
            self.__sp.pause_playback()
            log_msg("Playback paused")
        self.is_paused = True

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.connect_playing and self.is_paused:
            self.__sp.start_playback()
            log_msg("Playback unpaused")
        self.is_paused = False

    def onPlayBackEnded(self):
        pass

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        # set the connect_playing bool to indicate we are playing spotify connect content
        self.is_paused = False
        filename = ""
        while not filename:
            try:
                filename = self.getPlayingFile()
            except:
                xbmc.sleep(500)
        if "127.0.0.1:%s" % PROXY_PORT in filename:
            if not self.connect_playing and not self.connect_local and "silence" in filename:
                # we started playback with remote connect player
                self.connect_playing = True
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
        if self.ignore_seek:
            self.ignore_seek = False
        else:
            log_msg("Kodiplayer seekto: %s" %seekTime)
            if self.connect_local:
                self.ignore_seek = True
            self.__sp.seek_track(seekTime)

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        if self.connect_playing:
            self.__sp.pause_playback()
            log_msg("playback stopped")
        self.connect_playing = False
        self.connect_local = False

    def update_playlist(self):
        '''Update the playlist: add fake item at the end which allows us to skip'''
        if self.connect_local:
            url = "http://127.0.0.1:%s/track/nexttrack" % PROXY_PORT
        else:
            url = "plugin://plugin.audio.spotify/?action=next_track"
        self.__playlist.add(url)
        self.__playlist.add(url)
        
    def start_playback(self, track_id):
        self.connect_playing = True
        self.__playlist.clear()
        silenced = False
        if self.__direct_playback or not self.connect_local:
            silenced = True
        try:
            trackdetails = self.__sp.track(track_id)
            url, li = parse_spotify_track(trackdetails, silenced=silenced )
        except Exception as exc:
            # I've seen a few times that a track ID couldn't be recognized because the leading zero was stripped of
            track_id = "0%s" % track_id
            trackdetails = self.__sp.track(track_id)
            url, li = parse_spotify_track(trackdetails, silenced=silenced)
        self.__playlist.add(url, li)
        self.play()
        self.ignore_seek = True
        self.__sp.seek_track(0) # for now we always start a track at the beginning
        
