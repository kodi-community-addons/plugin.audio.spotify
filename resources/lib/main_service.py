#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    Spotify Player for Kodi
    main_service.py
    Background service which launches the librespot binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_token, LibreSpot, PROXY_PORT, kill_librespot, parse_spotify_track
from player_monitor import KodiPlayer
from webservice import WebService
from httpproxy import ProxyRunner
import xbmc
import xbmcaddon
import xbmcgui
import subprocess
import os
import sys
import xbmcvfs
import stat
import spotipy
import time
import threading
import thread
import StringIO

class MainService:
    '''our main background service running the various threads'''
    sp = None
    addon = None
    kodiplayer = None
    webservice = None
    librespot = None
    connect_daemon = None
    token_info = None

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        self.kodimonitor = xbmc.Monitor()
        self.librespot = LibreSpot()
        
        # spotipy and the webservice are always prestarted in the background
        # the auth key for spotipy will be set afterwards
        # the webserver is also used for the authentication callbacks from spotify api
        self.sp = spotipy.Spotify()
        direct_playback = self.addon.getSetting("direct_playback") == "true"
        self.kodiplayer = KodiPlayer(sp=self.sp, direct_playback=direct_playback)
        self.connect_daemon = ConnectDaemon(self.librespot, self.kodiplayer, direct_playback)
        
        self.proxy_runner = ProxyRunner(self.librespot)
        self.proxy_runner.start()
        webport = self.proxy_runner.get_port()
        log_msg('started webproxy at port {0}'.format(webport))

        # authenticate
        self.token_info = self.get_auth_token()
        if self.token_info:

            # initialize spotipy
            self.sp._auth = self.token_info["access_token"]
            me = self.sp.me()
            log_msg("Logged in to Spotify - Username: %s" % me["id"], xbmc.LOGNOTICE)
            log_msg("Userdetails: %s" % me, xbmc.LOGDEBUG)

            # start experimental spotify connect daemon
            if self.addon.getSetting("connect_player") == "true" and self.librespot.playback_supported:
                self.connect_daemon.start()

        # start mainloop
        self.main_loop()

    def main_loop(self):
        '''main loop which keeps our threads alive and refreshes the token'''
        while not self.kodimonitor.waitForAbort(5):
            # monitor logged in user
            username = self.addon.getSetting("username").decode("utf-8")
            if username and self.librespot.username != username:
                # username and/or password changed !
                self.switch_user()
            # monitor auth token expiration
            elif self.librespot.username and not self.token_info:
                # we do not yet have a token
                self.renew_token()
            elif self.token_info and self.token_info['expires_at'] - 60 <= (int(time.time())):
                # token needs refreshing !
                self.renew_token()
            elif not username and self.addon.getSetting("multi_account") == "true":
                # edge case where user sets multi user directly at first start
                # in that case copy creds to default
                username1 = self.addon.getSetting("username1").decode("utf-8")
                password1 = self.addon.getSetting("password1").decode("utf-8")
                if username1 and password1:
                    self.addon.setSetting("username", username1)
                    self.addon.setSetting("password", password1)
                    self.switch_user()
            elif self.addon.getSetting("playback_device") == "connect" and self.kodiplayer.connect_playing and not self.kodiplayer.connect_local:
                # monitor fake connect OSD for remote track changes
                cur_playback = self.sp.current_playback()
                if cur_playback["is_playing"]:
                    player_title = xbmc.getInfoLabel("MusicPlayer.Title").decode("utf-8")
                    if player_title and player_title != cur_playback["item"]["name"]:
                        log_msg("Next track requested by remote Spotify Connect player")
                        trackdetails = cur_playback["item"]
                        self.kodiplayer.start_playback(trackdetails["id"])
                elif not xbmc.getCondVisibility("Player.Paused"):
                    log_msg("Stop requested by Spotify Connect")
                    self.kodiplayer.stop()
                    
        # end of loop: we should exit
        self.close()

    def close(self):
        '''shutdown, perform cleanup'''
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        kill_librespot()
        #self.webservice.stop()
        self.proxy_runner.stop()
        if self.connect_daemon:
            self.connect_daemon.stop()
        self.kodiplayer.close()
        del self.kodiplayer
        del self.addon
        del self.kodimonitor
        log_msg('stopped', xbmc.LOGNOTICE)

    def get_auth_token(self):
        '''check for valid credentials and grab token'''
        auth_token = None
        username = self.addon.getSetting("username").decode("utf-8")
        password = self.addon.getSetting("password").decode("utf-8")
        if username and password:
            self.librespot.username = username
            self.librespot.password = password
            auth_token = get_token(self.librespot)
        if auth_token:
            log_msg("Retrieved auth token")
            # store authtoken as window prop for easy access by plugin entry
            xbmc.executebuiltin("SetProperty(spotify-token, %s, Home)" % auth_token['access_token'])
        return auth_token

    def switch_user(self):
        '''called whenever we switch to a different user/credentials'''
        log_msg("login credentials changed")
        if self.renew_token():
            xbmc.executebuiltin("Container.Refresh")
            me = self.sp.me()
            log_msg("Logged in to Spotify - Username: %s" % me["id"], xbmc.LOGNOTICE)
            # restart daemon
            if self.connect_daemon:
                self.connect_daemon.stop()
                self.connect_daemon.start()

    def renew_token(self):
        '''refresh the token'''
        self.token_info = self.get_auth_token()
        if self.token_info:
            log_msg("Authentication token updated...")
            # only update token info in spotipy object
            self.sp._auth = self.token_info['access_token']
            return True
        return False

class ConnectDaemon(threading.Thread):
    '''
        I couldn't make reading the audio from the stdout working reliable so instead
        this reads the output delayed to fake realtime playback
        note: the stdout of librespot can return the whole audio within a few seconds so that's why we need to simulate
        that it's outputted as stream
    '''
    __cur_track = None
    __librespot_proc = None
    __ignore_seek = False
    __sp = None

    def __init__(self, librespot, kodiplayer, direct_playback):
        self.__stop = False
        self.__librespot = librespot
        self.__kodiplayer = kodiplayer
        self.__direct_playback = direct_playback
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        while not self.__stop:
            log_msg("Start Spotify Connect Daemon")
            librespot_args = ["-v"]
            if not self.__direct_playback:
                librespot_args += ["--backend", "pipe"]
            self.__librespot_proc = self.__librespot.run_librespot(arguments=librespot_args)
            if not self.__direct_playback:
                thread.start_new_thread(self.fill_fake_buffer, ())
            while not self.__stop:
                line = self.__librespot_proc.stderr.readline().strip()
                if line:
                    # grab the track id from the stderr so our player knows which track is being played by the connect daemon
                    # Usefull in the scenario that another user connected to the connect daemon by using discovery
                    if "Loading track" in line and "[" in line and "]" in line:
                        # player is loading a new track !
                        track_id = line.split("[")[-1].split("]")[0]
                        if track_id != self.__cur_track:
                            self.__cur_track = track_id
                            if self.__kodiplayer.connect_playing:
                                self.__kodiplayer.connect_local = True
                                self.__kodiplayer.start_playback(track_id)
                                log_msg("Connect player requested playback of track %s" % track_id)
                            else:
                                log_msg("Connect player preloaded track %s" % track_id)
                    elif "command=Pause" in line and not self.__kodiplayer.is_paused:
                        log_msg("Pause requested by connect player")
                        self.__kodiplayer.pause()
                    elif "command=Stop" in line:
                        log_msg("Stop requested by connect player")
                        self.__kodiplayer.stop()
                    elif "command=Play" in line and self.__kodiplayer.is_paused:
                        log_msg("Resume requested by connect player")
                        self.__kodiplayer.pause()
                    elif "command=Play" in line and self.__cur_track and not self.__kodiplayer.connect_playing:
                        log_msg("Play requested by connect player")
                        self.__kodiplayer.connect_local = True
                        self.__kodiplayer.start_playback(self.__cur_track)
                    elif "command=Seek" in line:
                        if self.__kodiplayer.ignore_seek:
                            self.__kodiplayer.ignore_seek = False
                        else:
                            seekstr = line.split("command=Seek(")[1].replace(")","")
                            seek_sec = int(seekstr) / 1000
                            log_msg("Seek to %s seconds requested by connect player" % seek_sec)
                            self.__kodiplayer.seekTime(seek_sec)
                    
                    if not "TRACE:" in line:
                        log_msg(line, xbmc.LOGDEBUG)
                if self.__librespot_proc.returncode and self.__librespot_proc.returncode > 0 and not self.__stop:
                    # daemon crashed ? restart ?
                    break
                    
        log_msg("Stopped Spotify Connect Daemon")
        
    def fill_fake_buffer(self):
        '''emulate playback by just slowly reading the stdout'''
        # We could pick up this data in a buffer but it is almost impossible to keep it all in sync.
        # So instead we ignore the audio from the connect daemon completely and we just launch a standalone instanc eto play the track
        while not self.__stop:
            line = self.__librespot_proc.stdout.readline()
            xbmc.sleep(1)
            

    def stop(self):
        self.__stop = True
        if self.__librespot_proc:
            self.__librespot_proc.terminate()
        self.join(2)
