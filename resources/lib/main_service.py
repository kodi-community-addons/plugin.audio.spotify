#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    Spotify Player for Kodi
    main_service.py
    Background service which launches the spotty binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_token, Spotty, PROXY_PORT, kill_spotty
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


class MainService:
    '''our main background service running the various threads'''
    sp = None
    addon = None
    win = None
    kodiplayer = None
    webservice = None
    spotty = None
    connect_daemon = None
    token_info = None

    def __init__(self):
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        self.win = xbmcgui.Window(10000)
        self.kodimonitor = xbmc.Monitor()
        self.spotty = Spotty()
        
        # spotipy and the webservice are always prestarted in the background
        # the auth key for spotipy will be set afterwards
        # the webserver is also used for the authentication callbacks from spotify api
        self.sp = spotipy.Spotify()
        self.kodiplayer = KodiPlayer(sp=self.sp)
        self.webservice = WebService(sp=self.sp, kodiplayer=self.kodiplayer, spotty=self.spotty)
        self.webservice.start()

        # authenticate and grab token
        self.token_info = self.get_auth_token()

        if self.token_info:

            # initialize spotipy
            self.sp._auth = self.token_info["access_token"]
            me = self.sp.me()
            log_msg("Logged in to Spotify - Username: %s" % me["id"], xbmc.LOGNOTICE)
            log_msg("Userdetails: %s" % me, xbmc.LOGDEBUG)

            # start experimental spotify connect daemon
            if self.addon.getSetting("connect_player") == "true" and self.spotty.playback_supported:
                self.connect_daemon = ConnectDaemon(spotty=self.spotty)
                self.connect_daemon.start()
                self.kodiplayer.playerid = self.get_playerid()

            # set flag that local playback is supported
            if self.spotty.playback_supported:
                self.win.setProperty("spotify.supportsplayback", "true")
            else:
                self.win.clearProperty("spotify.supportsplayback")

            # start mainloop
            self.main_loop()

    def main_loop(self):
        '''main loop which keeps our threads alive and refreshes the token'''
        while not self.kodimonitor.waitForAbort(5):
            # monitor logged in user
            username = self.addon.getSetting("username").decode("utf-8")
            password = self.addon.getSetting("password").decode("utf-8")
            if (self.spotty.username != username) or (self.spotty.password != password):
                # username and/or password changed !
                self.switch_user()
            # monitor auth token expiration
            if self.token_info['expires_at'] - 60 <= (int(time.time())):
                # token expired !
                self.renew_token()
        # end of loop: we should exit
        self.close()

    def close(self):
        '''shutdown, perform cleanup'''
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        kill_spotty()
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
        # loop untill we have a valid token
        while not self.kodimonitor.abortRequested():
            username = self.addon.getSetting("username").decode("utf-8")
            password = self.addon.getSetting("password").decode("utf-8")
            if username and password:
                self.spotty.username = username
                self.spotty.password = password
                auth_token = get_token(self.spotty)
            if auth_token:
                log_msg("Retrieved auth token")
                break
            else:
                log_msg("waiting for credentials...", xbmc.LOGDEBUG)
                self.kodimonitor.waitForAbort(2)
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
                self.connect_daemon = ConnectDaemon(spotty=self.spotty)
                self.connect_daemon.start()
                playerid = self.get_playerid()
                self.kodiplayer.playerid = playerid

    def renew_token(self):
        '''refresh the token'''
        self.token_info = self.get_auth_token()
        if self.token_info:
            log_msg("Authentication token updated...")
            # only update token info in spotipy object
            self.sp._auth = self.token_info['access_token']
            return True
        return False

    def get_playerid(self):
        '''get the ID which is assigned to our virtual connect device'''
        playername = self.spotty.playername
        playerid = ""
        count = 0
        while not playerid and not self.kodimonitor.abortRequested():
            xbmc.sleep(1000)
            count += 1
            if count == 10:
                break
            log_msg("waiting for playerid", xbmc.LOGNOTICE)
            devices = self.sp.devices()
            if devices and devices.get("devices"):
                for device in devices["devices"]:
                    if device["name"] == playername:
                        playerid = device["id"]
        log_msg("Playerid: %s" % playerid, xbmc.LOGDEBUG)
        return playerid


class ConnectDaemon(threading.Thread):
    '''
        I couldn't make reading the audio from the stdout working reliable so instead
        this reads the output delayed to fake realtime playback
        note: the stdout of spotty can return the whole audio within a few seconds so that's why we need to simulate
        that it's outputted as stream
    '''

    def __init__(self, *args, **kwargs):
        spotty_args = ["--onstart", "curl http://localhost:%s/playercmd/start" % PROXY_PORT,
                       "--onstop", "curl http://localhost:%s/playercmd/stop" % PROXY_PORT,
                       "--onchange", "curl http://localhost:%s/playercmd/change" % PROXY_PORT]
        spotty = kwargs.get("spotty")
        self.__spotty = spotty.run_spotty(arguments=spotty_args)
        threading.Thread.__init__(self, *args)

    def run(self):
        log_msg("Start Spotify Connect Daemon")
        self.__stop = False
        while not self.__stop:
            line = self.__spotty.stdout.readline()
            xbmc.sleep(5)
        log_msg("Stopped Spotify Connect Daemon")

    def stop(self):
        self.__spotty.terminate()
        self.__stop = True
        self.join(0.1)
