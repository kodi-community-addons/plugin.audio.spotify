#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    Spotify Player for Kodi
    main_service.py
    Background service which launches the spotty binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_token, start_spotty, SpottyDaemon, PROXY_PORT, get_playername, get_spotty_binary
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


class MainService:
    '''our main background service running the various threads'''
    sp = None
    username = None
    addon = None
    win = None
    kodiplayer = None
    webservice = None
    spotty_daemon = None

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        self.win = xbmcgui.Window(10000)
        self.kodimonitor = xbmc.Monitor()

        # set flag that local playback is supported
        playback_supported = get_spotty_binary() is not None
        if playback_supported:
            self.win.setProperty("spotify.supportsplayback", "true")
        else:
            self.win.clearProperty("spotify.supportsplayback")

        # initialize Spotipy
        self.init_spotipy()

        # start experimental spotify connect daemon
        if self.addon.getSetting("connect_player") == "true":
            self.spotty_daemon = SpottyDaemon()
            self.spotty_daemon.start()
            playerid = self.get_playerid()
            self.kodiplayer = KodiPlayer(sp=self.sp, playerid=playerid)

        # start the webproxy which hosts the audio
        self.webservice = WebService(sp=self.sp, kodiplayer=self.kodiplayer)
        self.webservice.start()

        # start mainloop
        self.main_loop()

    def main_loop(self):
        '''main loop which monitors our other threads and keeps them alive'''
        loop_count = 0
        refresh_interval = 3500
        while not self.kodimonitor.waitForAbort(1):
            # monitor logged in user and spotipy session
            username = self.addon.getSetting("username").decode("utf-8")
            if (self.username != username) or (loop_count >= refresh_interval):
                loop_count = 0
                refresh_interval = self.init_spotipy()
            else:
                loop_count += 1
        # end of loop: we should exit
        self.close()

    def close(self):
        '''shutdown, perform cleanup'''
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        if self.spotty_daemon:
            self.spotty_daemon.stop()
            self.kodiplayer.close()
            del self.kodiplayer
        self.webservice.stop()
        del self.win
        del self.addon
        del self.kodimonitor
        log_msg('stopped', xbmc.LOGNOTICE)

    def init_spotipy(self):
        '''initialize spotipy class and refresh auth token'''
        # get authorization key
        auth_token = None
        while not auth_token:
            username = self.addon.getSetting("username").decode("utf-8")
            password = self.addon.getSetting("password").decode("utf-8")
            if username and password:
                self.username = username
                auth_token = get_token(username, password)
            if not auth_token:
                log_msg("waiting for credentials...", xbmc.LOGDEBUG)
                if self.kodimonitor.waitForAbort(5):
                    return  # exit if abort requested

        # store authtoken as window prop for easy access by plugin entry
        self.win.setProperty("spotify-token", auth_token['access_token'])

        # initialize spotipy
        if not self.sp:
            self.sp = spotipy.Spotify(auth=auth_token['access_token'])
            me = self.sp.me()
            log_msg("Logged in to Spotify - Username: %s" % me["id"], xbmc.LOGNOTICE)
            log_msg("Userdetails: %s" % me, xbmc.LOGDEBUG)
        else:
            self.sp._auth = auth_token['access_token']
            log_msg("Authentication token updated...")

        # return the remaining seconds before the token expires so we can refresh it in time
        token_refresh = auth_token['expires_at'] - int(time.time()) - 30
        log_msg("token refresh needed in %s seconds" % token_refresh, xbmc.LOGDEBUG)
        return token_refresh

    def get_playerid(self):
        '''get the ID which is assigned to our virtual connect device'''
        playername = get_playername()
        playerid = ""
        while not playerid:
            xbmc.sleep(1000)
            log_msg("waiting for playerid", xbmc.LOGDEBUG)
            for device in self.sp.devices()["devices"]:
                if device["name"] == playername:
                    playerid = device["id"]
        log_msg("Playerid: %s" % playerid, xbmc.LOGDEBUG)
        return playerid
