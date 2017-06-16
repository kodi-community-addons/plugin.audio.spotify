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
    win = None
    kodiplayer = None
    webservice = None
    librespot = None
    connect_daemon = None
    token_info = None

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        self.win = xbmcgui.Window(10000)
        self.kodimonitor = xbmc.Monitor()
        self.librespot = LibreSpot()
        self.connect_daemon = ConnectDaemon(librespot=self.librespot)
        
        # spotipy and the webservice are always prestarted in the background
        # the auth key for spotipy will be set afterwards
        # the webserver is also used for the authentication callbacks from spotify api
        self.sp = spotipy.Spotify()
        self.kodiplayer = KodiPlayer(sp=self.sp)
        self.webservice = WebService(sp=self.sp, kodiplayer=self.kodiplayer, librespot=self.librespot, connect_daemon=self.connect_daemon)
        self.webservice.start()

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
                        log_msg("Next track requested by Spotify Connect")
                        trackdetails = cur_playback["item"]
                        url, li = parse_spotify_track( cur_playback["item"], is_remote=True)
                        self.kodiplayer.playlist.clear()
                        self.kodiplayer.playlist.add(url, li)
                        self.kodiplayer.play()
                elif not xbmc.getCondVisibility("Player.Paused"):
                    log_msg("Stop requested by Spotify Connect")
                    self.kodiplayer.stop()
                    
        # end of loop: we should exit
        self.close()

    def close(self):
        '''shutdown, perform cleanup'''
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        kill_librespot()
        self.webservice.stop()
        if self.connect_daemon:
            self.connect_daemon.stop()
        self.kodiplayer.close()
        del self.kodiplayer
        del self.win
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
            self.win.setProperty("spotify-token", auth_token['access_token'])
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
    cur_track = ""
    librespot_proc = None

    def __init__(self, *args, **kwargs):
        self.__stop = False
        self.librespot = kwargs.get("librespot")
        threading.Thread.__init__(self, *args)

    def run(self):
        while not self.__stop:
            log_msg("Start Spotify Connect Daemon")
            librespot_args = ["--onstart", "curl -s -f -m 2 http://localhost:%s/playercmd/start" % PROXY_PORT,
                           "--onstop", "curl -s -f -m 2  http://localhost:%s/playercmd/stop" % PROXY_PORT,
                           "--onchange", "curl -s -f -m 2  http://localhost:%s/playercmd/change" % PROXY_PORT,
                           "--backend", "pipe"]
            self.librespot_proc = self.librespot.run_librespot(arguments=librespot_args)
            thread.start_new_thread(self.fill_fake_buffer, ())
            while not self.__stop:
                line = self.librespot_proc.stderr.readline().strip()
                if line:
                    # grab the track id from the stderr so our player knows which track is being played by the connect daemon
                    # Usefull in the scenario that another user connected to the connect daemon by using discovery
                    if "track" in line and "[" in line and "]" in line:
                        self.cur_track = line.split("[")[-1].split("]")[0]
                    log_msg(line, xbmc.LOGDEBUG)
                if self.librespot_proc.returncode and self.librespot_proc.returncode > 0 and not self.__stop:
                    # daemon crashed ? restart ?
                    break
                    
        log_msg("Stopped Spotify Connect Daemon")
        
    def fill_fake_buffer(self):
        '''emulate playback by just slowly reading the stdout'''
        # We could pick up this data in a buffer but it is almost impossible to keep it all in sync.
        # So instead we ignore the audio from the connect daemon completely and we just launch a standalone instanc eto play the track
        while not self.__stop:
            line = self.librespot_proc.stdout.readline()
            xbmc.sleep(100)

    def stop(self):
        self.__stop = True
        if self.librespot_proc:
            self.librespot_proc.terminate()
        self.join(0.5)
