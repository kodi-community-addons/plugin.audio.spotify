#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception, parse_spotify_track, PROXY_PORT
import xbmc
import xbmcgui
from urllib import quote_plus
import threading
import thread


class ConnectPlayer(threading.Thread, xbmc.Player):
    '''Simulate a Spotify Connect player with the Kodi player'''
    connect_playing = False  # spotify connect is playing
    connect_local = False  # connect player is this device
    daemon_active = False
    username = None
    __playlist = None
    __exit = False
    __is_paused = False
    __cur_track = None
    __spotty_proc = None
    __ignore_seek = False
    __sp = None

    def __init__(self, **kwargs):
        self.__sp = kwargs.get("sp")
        self.__spotty = kwargs.get("spotty")
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self, **kwargs)
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def close(self):
        '''cleanup on exit'''
        self.stop_thread()
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
        while not filename:
            try:
                filename = self.getPlayingFile()
            except:
                xbmc.sleep(500)
        if "localhost:%s" % PROXY_PORT in filename:
            if not self.connect_playing and "connect=true" in filename:
                # we started playback with (remote) connect player
                log_msg("Playback started of Spotify Connect stream")
                # check username of connect player
                self.__spotty.get_username()
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

    def run(self):
        self.daemon_active = True
        while not self.__exit:
            log_msg("Start Spotify Connect Daemon")
            spotty_args = ["--lms", "localhost:52308/lms", "--player-mac", "None"]
            self.__spotty_proc = self.__spotty.run_spotty(arguments=spotty_args)
            thread.start_new_thread(self.fill_fake_buffer, ())
            while not self.__exit:
                line = self.__spotty_proc.stderr.readline().strip()
                if line:
                    log_msg(line, xbmc.LOGDEBUG)
                if self.__spotty_proc.returncode and self.__spotty_proc.returncode > 0 and not self.__exit:
                    # daemon crashed ? restart ?
                    log_msg("spotty crash?")
                    break
        self.daemon_active = False
        log_msg("Stopped Spotify Connect Daemon")

    def fill_fake_buffer(self):
        '''emulate playback by just slowly reading the stdout'''
        # We could pick up this data in a buffer but it is almost impossible to keep it all in sync.
        # So instead we ignore the audio from the connect daemon completely and we
        # just launch a standalone instance to play the track
        while not self.__exit:
            line = self.__spotty_proc.stdout.readline()
            xbmc.sleep(1)

    def stop_thread(self):
        self.__exit = True
        if self.__spotty_proc:
            self.__spotty_proc.terminate()
            self.join(2)
