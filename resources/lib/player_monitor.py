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
    __playlist = None
    __exit = False
    __is_paused = False
    __cur_track = None
    __librespot_proc = None
    __ignore_seek = False
    __sp = None

    def __init__(self, **kwargs):
        self.__sp = kwargs.get("sp")
        self.__direct_playback = kwargs.get("direct_playback")
        self.__librespot = kwargs.get("librespot")
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
        if self.__ignore_seek:
            self.__ignore_seek = False
        else:
            log_msg("Kodiplayer seekto: %s" % seekTime)
            if self.connect_local:
                self.__ignore_seek = True
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
            url = "http://localhost:%s/track/nexttrack" % PROXY_PORT
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
            url, li = parse_spotify_track(trackdetails, silenced=silenced)
        except Exception as exc:
            # I've seen a few times that a track ID couldn't be recognized because the leading zero was stripped of
            track_id = "0%s" % track_id
            trackdetails = self.__sp.track(track_id)
            url, li = parse_spotify_track(trackdetails, silenced=silenced)
        self.__playlist.add(url, li)
        self.play()
        self.__ignore_seek = True
        if self.connect_local and not self.__direct_playback:
            self.__sp.seek_track(0)  # for now we always start a track at the beginning

    def run(self):
        while not self.__exit:
            log_msg("Start Spotify Connect Daemon")
            librespot_args = ["-v"]
            if not self.__direct_playback:
                librespot_args += ["--backend", "pipe"]
            self.__librespot_proc = self.__librespot.run_librespot(arguments=librespot_args)
            if not self.__direct_playback:
                thread.start_new_thread(self.fill_fake_buffer, ())
            while not self.__exit:
                line = self.__librespot_proc.stderr.readline().strip()
                if line:
                    # grab the track id from the stderr so our player knows which track is being played by the connect daemon
                    # Usefull in the scenario that another user connected to the connect daemon by using discovery
                    if "Loading track" in line and "[" in line and "]" in line:
                        # player is loading a new track !
                        track_id = line.split("[")[-1].split("]")[0]
                        if track_id != self.__cur_track:
                            self.__cur_track = track_id
                            if self.connect_playing:
                                self.connect_local = True
                                self.start_playback(track_id)
                                log_msg("Connect player requested playback of track %s" % track_id)
                            else:
                                log_msg("Connect player preloaded track %s" % track_id)
                    elif "command=Pause" in line and not self.__is_paused:
                        log_msg("Pause requested by connect player")
                        self.pause()
                    elif "command=Stop" in line:
                        log_msg("Stop requested by connect player")
                        self.stop()
                    elif "command=Play" in line and self.__is_paused:
                        log_msg("Resume requested by connect player")
                        self.pause()
                    elif "command=Play" in line and self.__cur_track and not self.connect_playing:
                        log_msg("Play requested by connect player")
                        self.connect_local = True
                        self.start_playback(self.__cur_track)
                    elif "command=Seek" in line and self.connect_playing:
                        if self.__ignore_seek:
                            self.__ignore_seek = False
                        else:
                            seekstr = line.split("command=Seek(")[1].replace(")", "")
                            seek_sec = int(seekstr) / 1000
                            log_msg("Seek to %s seconds requested by connect player" % seek_sec)
                            self.seekTime(seek_sec)
                    if not "TRACE:" in line:
                        log_msg(line, xbmc.LOGDEBUG)
                if self.__librespot_proc.returncode and self.__librespot_proc.returncode > 0 and not self.__exit:
                    # daemon crashed ? restart ?
                    break

        log_msg("Stopped Spotify Connect Daemon")

    def fill_fake_buffer(self):
        '''emulate playback by just slowly reading the stdout'''
        # We could pick up this data in a buffer but it is almost impossible to keep it all in sync.
        # So instead we ignore the audio from the connect daemon completely and we
        # just launch a standalone instanc eto play the track
        while not self.__exit:
            line = self.__librespot_proc.stdout.readline()
            xbmc.sleep(1)

    def stop_thread(self):
        self.__exit = True
        if self.__librespot_proc:
            self.__librespot_proc.terminate()
        self.join(2)
