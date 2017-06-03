#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    spotty Player for Kodi
    utils.py
    Various helper methods
'''

import xbmc
import xbmcvfs
import xbmcgui
import os
import stat
import sys
import urllib
from traceback import format_exc
import requests
import subprocess
import xbmcaddon
import struct
import random
import time
import math


PROXY_PORT = 52308

try:
    import simplejson as json
except Exception:
    import json

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


ADDON_ID = "plugin.audio.spotify"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)
CHMOD_DONE = False
requests.packages.urllib3.disable_warnings()  # disable ssl warnings
SCOPE = [
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-follow-modify",
    "user-follow-read",
    "user-library-read",
    "user-library-modify",
    "user-read-private",
    "user-read-email",
    "user-read-birthdate",
    "user-top-read"]
CLIENTID = '4940f5cc79b149af9f71d5ef9319eff0'
CLIENT_SECRET = '779F4D60BD3B42E29984ADF423F19688'


try:
    from multiprocessing.pool import ThreadPool
    SUPPORTS_POOL = True
except Exception:
    SUPPORTS_POOL = False


def log_msg(msg, loglevel=xbmc.LOGNOTICE):
    '''log message to kodi log'''
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("%s --> %s" % (ADDON_ID, msg), level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGDEBUG)
    log_msg("Exception in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGWARNING)


def kill_spotty():
    '''make sure we don't have any (remaining) spotty processes running before we start one'''
    if xbmc.getCondVisibility("System.Platform.Windows"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(["taskkill", "/IM", "spotty.exe"], startupinfo=startupinfo, shell=True)
    else:
        os.system("killall spotty")


def get_token(spotty):
    # get authentication token for api - prefer cached version
    token_info = None
    try:
        # try to get a token with spotty
        token_info = request_token_spotty(spotty)
        # request new token with web flow
        if not token_info:
            token_info = request_token_web(spotty.username)
    except Exception as exc:
        log_msg("Couldn't request authentication token. Username/password error ?")
        log_exception("utils.get_token", exc)
        token_info = None
    return token_info


def request_token_spotty(spotty):
    '''request token by using the spotty binary'''
    token_info = None
    if spotty.playback_supported:
        try:
            args = ["-t", "--client-id", CLIENTID, "--scope", ",".join(SCOPE)]
            spotty = spotty.run_spotty(arguments=args)
            stdout, stderr = spotty.communicate()
            result = eval(stdout)
            # transform token info to spotipy compatible format
            token_info = {}
            token_info["access_token"] = result["accessToken"]
            token_info["expires_in"] = result["expiresIn"]
            token_info["token_type"] = result["tokenType"]
            token_info["scope"] = ' '.join(result["scope"])
            token_info['expires_at'] = int(time.time()) + token_info['expires_in']
            token_info['refresh_token'] = result["accessToken"]
            log_msg("Token from spotty: %s" % token_info, xbmc.LOGDEBUG)
        except Exception as exc:
            log_exception(__name__, exc)
    return token_info


def request_token_web(username):
    '''request the (initial) auth token by webbrowser'''
    from spotipy import oauth2
    cache_path = u"special://profile/addon_data/%s/%s.cache" % (ADDON_ID, normalize_string(username))
    cache_path = xbmc.translatePath(cache_path).decode("utf-8")
    scope = " ".join(SCOPE)
    redirect_url = 'http://localhost:%s/callback' % PROXY_PORT
    sp_oauth = oauth2.SpotifyOAuth(CLIENTID, CLIENT_SECRET, redirect_url, scope=scope, cache_path=cache_path)
    # get token from cache
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        # request token by using the webbrowser
        p = None
        auth_url = sp_oauth.get_authorize_url()
        
        # show message to user that the browser is going to be launched
        dialog = xbmcgui.Dialog()
        header = xbmc.getInfoLabel("System.AddonTitle(%s)" %ADDON_ID).decode("utf-8")
        msg = xbmc.getInfoLabel("$ADDON[%s 11049]" %ADDON_ID).decode("utf-8")
        dialog.ok(header, msg)
        del dialog

        if xbmc.getCondVisibility("System.Platform.Android"):
            # for android we just launch the default android browser
            xbmc.executebuiltin("StartAndroidActivity(,android.intent.action.VIEW,,%s)" % auth_url)
        else:
            # use webbrowser module
            import webbrowser
            log_msg("Launching system-default browser")
            webbrowser.open(auth_url, new=1)

        count = 0
        while not xbmc.getInfoLabel("Window(Home).Property(spotify-token-info)"):
            log_msg("Waiting for authentication token...")
            xbmc.sleep(2000)
            if count == 60:
                break
            count += 1

        response = xbmc.getInfoLabel("Window(Home).Property(spotify-token-info)")
        xbmc.executebuiltin("ClearProperty(spotify-token-info,Home)")
        if response:
            response = sp_oauth.parse_response_code(response)
            token_info = sp_oauth.get_access_token(response)
        xbmc.sleep(2000)  # allow enough time for the webbrowser to stop
    log_msg("Token from web: %s" % token_info, xbmc.LOGDEBUG)
    return token_info


def create_wave_header(duration):
    '''generate a wave header for the stream'''
    file = StringIO.StringIO()
    numsamples = 44100 * duration
    channels = 2
    samplerate = 44100
    bitspersample = 16

    # Generate format chunk
    format_chunk_spec = "<4sLHHLLHH"
    format_chunk = struct.pack(
        format_chunk_spec,
        "fmt ",  # Chunk id
        16,  # Size of this chunk (excluding chunk id and this field)
        1,  # Audio format, 1 for PCM
        channels,  # Number of channels
        samplerate,  # Samplerate, 44100, 48000, etc.
        samplerate * channels * (bitspersample / 8),  # Byterate
        channels * (bitspersample / 8),  # Blockalign
        bitspersample,  # 16 bits for two byte samples, etc.
    )
    # Generate data chunk
    data_chunk_spec = "<4sL"
    datasize = numsamples * channels * (bitspersample / 8)
    data_chunk = struct.pack(
        data_chunk_spec,
        "data",  # Chunk id
        int(datasize),  # Chunk size (excluding chunk id and this field)
    )
    sum_items = [
        #"WAVE" string following size field
        4,
        #"fmt " + chunk size field + chunk size
        struct.calcsize(format_chunk_spec),
        # Size of data chunk spec + data size
        struct.calcsize(data_chunk_spec) + datasize
    ]
    # Generate main header
    all_cunks_size = int(sum(sum_items))
    main_header_spec = "<4sL4s"
    main_header = struct.pack(
        main_header_spec,
        "RIFF",
        all_cunks_size,
        "WAVE"
    )
    # Write all the contents in
    file.write(main_header)
    file.write(format_chunk)
    file.write(data_chunk)

    return file.getvalue(), all_cunks_size + 8


def process_method_on_list(method_to_run, items):
    '''helper method that processes a method on each listitem with pooling if the system supports it'''
    all_items = []
    if SUPPORTS_POOL:
        pool = ThreadPool()
        try:
            all_items = pool.map(method_to_run, items)
        except Exception:
            # catch exception to prevent threadpool running forever
            log_msg(format_exc(sys.exc_info()))
            log_msg("Error in %s" % method_to_run)
        pool.close()
        pool.join()
    else:
        all_items = [method_to_run(item) for item in items]
    all_items = filter(None, all_items)
    return all_items


def get_track_rating(popularity):
    if popularity == 0:
        return 0
    else:
        return int(math.ceil(popularity * 6 / 100.0)) - 1


def parse_spotify_track(track, is_album_track=True, is_connect=False):
    if track.get("images"):
        thumb = track["images"][0]['url']
    elif track['album'].get("images"):
        thumb = track['album']["images"][0]['url']
    else:
        thumb = ""
    
    if is_connect:
        url = "http://localhost:%s/connect/%s" % (PROXY_PORT, track['id'])
    else:
        url = "http://localhost:%s/track/%s" % (PROXY_PORT, track['id'])

    li = xbmcgui.ListItem(
        track['name'],
        path=url,
        iconImage="DefaultMusicSongs.png",
        thumbnailImage=thumb
    )
    infolabels = {
        "title": track['name'],
        "genre": " / ".join(track["album"].get("genres", [])),
        "year": int(track["album"].get("release_date", "0").split("-")[0]),
        "album": track['album']["name"],
        "artist": " / ".join([artist["name"] for artist in track["artists"]]),
        "rating": str(get_track_rating(track["popularity"])),
        "duration": track["duration_ms"] / 1000
    }
    if is_album_track:
        infolabels["tracknumber"] = track["track_number"]
        infolabels["discnumber"] = track["disc_number"]
    li.setInfo(type="Music", infoLabels=infolabels)
    li.setProperty("spotifytrackid", track['id'])
    li.setContentLookup(False)
    li.setProperty('do_not_analyze', 'true')
    li.setMimeType("audio/wave")
    return url, li


def get_chunks(data, chunksize):
    return[data[x:x + chunksize] for x in xrange(0, len(data), chunksize)]


def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding, "ignore")
    except:
        return text


def try_decode(text, encoding="utf-8"):
    try:
        return text.decode(encoding, "ignore")
    except:
        return text


def normalize_string(text):
    import unicodedata
    text = text.replace(":", "")
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = text.replace("<", "")
    text = text.replace(">", "")
    text = text.replace("*", "")
    text = text.replace("?", "")
    text = text.replace('|', "")
    text = text.replace('(', "")
    text = text.replace(')', "")
    text = text.replace("\"", "")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', try_decode(text))
    return text


class Spotty(object):
    '''
        spotty is wrapped into a seperate class to store common properties
        this is done to prevent hitting a kodi issue where calling one of the infolabel methods
        causes a crash of the playback
    '''
    username = None
    password = None
    playback_supported = False
    playername = None
    supports_discovery = True
    __spotty_binary = None

    def __init__(self):
        '''initialize with default values'''
        addon = xbmcaddon.Addon(id=ADDON_ID)
        self.username = addon.getSetting("username").decode("utf-8")
        self.password = addon.getSetting("password").decode("utf-8")
        del addon
        self.playername = self.get_playername()
        self.__spotty_binary = self.get_spotty_binary()
        if self.__spotty_binary:
            self.playback_supported = True
            xbmc.executebuiltin("SetProperty(spotify.supportsplayback, true, Home)")

    def run_spotty(self, arguments=None, discovery=False):
        '''On supported platforms we include spotty binary'''
        if self.playback_supported:
            try:
                args = [
                    self.__spotty_binary,
                    "-n", self.playername,
                    "-u", self.username,
                    "-p", self.password
                ]
                if not discovery:
                    # discovery is disabled for now untill we work around grabbing the stream directly
                    args.append("--disable-discovery")
                if arguments:
                    args += arguments
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
                return subprocess.Popen(args, startupinfo=startupinfo, stdout=subprocess.PIPE, bufsize=0)
            except Exception as exc:
                log_exception(__name__, exc)
        return None

    def get_spotty_binary(self):
        '''find the correct spotty binary belonging to the platform'''
        sp_binary = None
        if xbmc.getCondVisibility("System.Platform.Windows"):
            sp_binary = os.path.join(os.path.dirname(__file__), "spotty", "windows", "spotty.exe")
            self.supports_discovery = False
        elif xbmc.getCondVisibility("System.Platform.OSX"):
            sp_binary = os.path.join(os.path.dirname(__file__), "spotty", "macos", "spotty")
            st = os.stat(sp_binary)
            os.chmod(sp_binary, st.st_mode | stat.S_IEXEC)
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            # try to find out the correct architecture by trial and error
            import platform
            architecture = platform.machine()
            if architecture.startswith('i686') or architecture.startswith('i386'):
                sp_binary = os.path.join(os.path.dirname(__file__), "spotty", "linux_x86", "spotty")
            elif architecture.startswith('AMD64') or architecture.startswith('x86_64'):
                # always use 32 bits binary because the 64 bits is somehow failing to play audio
                sp_binary = os.path.join(os.path.dirname(__file__), "spotty", "linux_x86", "spotty")
            else:
                # for arm cpu's we just try it out
                for item in ["spotty-muslhf", "spotty-hf"]:
                    bin_path = os.path.join(os.path.dirname(__file__), "spotty", "linux_arm", item)
                    st = os.stat(bin_path)
                    os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
                    try:
                        args = [bin_path, "-n", "test", "--check"]
                        sp_exec = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
                        stdout, stderr = sp_exec.communicate()
                        if "ok" in stdout:
                            sp_binary = bin_path
                            log_exc("Architecture detected")
                            break
                    except Exception as exc:
                        log_exception(__name__, exc)
            if sp_binary:
                st = os.stat(sp_binary)
                os.chmod(sp_binary, st.st_mode | stat.S_IEXEC)
            else:
                log_msg("Failed to detect architecture or platform not supported !")
        else:
            log_msg("Unsupported platform! - for iOS and Android you need to install a spotify app yourself and make sure it's running in the background.")
        return sp_binary

    @staticmethod
    def get_playername():
        playername = xbmc.getInfoLabel("System.FriendlyName").decode("utf-8")
        if playername == "Kodi":
            import socket
            playername = "Kodi (%s)" % socket.gethostname()
        return playername
