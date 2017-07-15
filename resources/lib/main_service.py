#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    Spotify Player for Kodi
    main_service.py
    Background service which launches the spotty binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_token, Spotty, PROXY_PORT, kill_spotty, parse_spotify_track
from player_monitor import ConnectPlayer
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
    connect_player = None
    webservice = None
    spotty = None
    token_info = None

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        self.kodimonitor = xbmc.Monitor()
        self.spotty = Spotty()

        # spotipy and the webservice are always prestarted in the background
        # the auth key for spotipy will be set afterwards
        # the webserver is also used for the authentication callbacks from spotify api
        self.sp = spotipy.Spotify()
        self.connect_player = ConnectPlayer(sp=self.sp, spotty=self.spotty)

        self.proxy_runner = ProxyRunner(self.spotty)
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

            # start experimental spotify connect daemon
            if self.addon.getSetting("connect_player") == "true" and self.spotty.playback_supported:
                self.connect_player.start()

        # start mainloop
        self.main_loop()

    def main_loop(self):
        '''main loop which keeps our threads alive and refreshes the token'''
        loop_timer = 5
        while not self.kodimonitor.waitForAbort(loop_timer):
            # monitor logged in user
            username = self.addon.getSetting("username").decode("utf-8")
            if username and self.spotty.username != username:
                # username and/or password changed !
                self.switch_user()
            # monitor auth token expiration
            elif self.spotty.username and not self.token_info:
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
            elif self.connect_player.connect_playing:
                # monitor fake connect OSD for remote track changes
                loop_timer = 2
                cur_playback = self.sp.current_playback()
                if cur_playback["is_playing"]:
                    player_title = xbmc.getInfoLabel("MusicPlayer.Title").decode("utf-8")
                    if player_title and player_title != cur_playback["item"]["name"]:
                        log_msg("Next track requested by Spotify Connect player")
                        trackdetails = cur_playback["item"]
                        self.connect_player.start_playback(trackdetails["id"])
                elif not xbmc.getCondVisibility("Player.Paused"):
                    log_msg("Stop requested by Spotify Connect")
                    self.connect_player.stop()
            else:
                loop_timer = 5

        # end of loop: we should exit
        self.close()

    def close(self):
        '''shutdown, perform cleanup'''
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        kill_spotty()
        self.proxy_runner.stop()
        self.connect_player.close()
        del self.connect_player
        del self.addon
        del self.kodimonitor
        log_msg('stopped', xbmc.LOGNOTICE)

    def get_auth_token(self):
        '''check for valid credentials and grab token'''
        auth_token = None
        username = self.addon.getSetting("username").decode("utf-8")
        password = self.addon.getSetting("password").decode("utf-8")
        if username and password:
            self.spotty.username = username
            self.spotty.password = password
            auth_token = get_token(self.spotty)
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
            if self.connect_player.daemon_active:
                self.connect_player.stop_thread()
                audio_device = self.addon.getSetting("audio_device") == "true"
                self.connect_player = ConnectPlayer(sp=self.sp, audio_device=audio_device, spotty=self.spotty)
                self.connect_player.start()

    def renew_token(self):
        '''refresh the token'''
        self.token_info = self.get_auth_token()
        if self.token_info:
            log_msg("Authentication token updated...")
            # only update token info in spotipy object
            self.sp._auth = self.token_info['access_token']
            return True
        return False
