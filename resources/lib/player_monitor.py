#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception, parse_spotify_track, PROXY_PORT
import xbmc
import xbmcgui
from urllib import quote_plus
import threading
import thread


class ConnectPlayer(xbmc.Player):
    '''Simulate a Spotify Connect player with the Kodi player'''
    connect_playing = False  # spotify connect is playing
    connect_local = False  # connect player is this device
    username = None
    __playlist = None
    __exit = False
    __is_paused = False
    __cur_track = None
    __ignore_seek = False
    __sp = None

    def __init__(self, **kwargs):
        self.__sp = kwargs.get("sp")
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self, **kwargs)

    def close(self):
        '''cleanup on exit'''
        del self.__playlist

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.connect_playing and not self.__is_paused:
            self.__sp.pause_playback()
            log_msg("Playback paused")
        self.__is_paused = True

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.connect_playing and self.__is_paused:
            self.__sp.start_playback()
            log_msg("Playback unpaused")
        self.__is_paused = False

    def onPlayBackEnded(self):
        pass

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        # set the connect_playing bool to indicate we are playing spotify connect content
        self.__is_paused = False
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
        if self.connect_playing:
            try:
                self.__sp.pause_playback()
            except Exception:
                pass
            log_msg("playback stopped")
        self.connect_playing = False
        self.connect_local = False

    def update_playlist(self):
        '''Update the playlist: add fake item at the end which allows us to skip'''
        if self.connect_local:
            url = "http://localhost:%s/nexttrack" % PROXY_PORT
        else:
            url = "plugin://plugin.audio.spotify/?action=next_track"
        self.__playlist.add(url)
        self.__playlist.add(url)

    def start_playback(self, track_id):
        self.connect_playing = True
        self.__playlist.clear()
        silenced = False
        if not self.connect_local:
            silenced = True
        trackdetails = self.__sp.track(track_id)
        url, li = parse_spotify_track(trackdetails, silenced=silenced)
        self.__playlist.add(url, li)
        self.play()
        self.__ignore_seek = True
        if self.connect_local:
            self.__sp.seek_track(0)  # for now we always start a track at the beginning
