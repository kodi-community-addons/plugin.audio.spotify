#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    librespot Player for Kodi
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


def kill_librespot():
    '''make sure we don't have any (remaining) librespot processes running before we start one'''
    if xbmc.getCondVisibility("System.Platform.Windows"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(["taskkill", "/IM", "librespot.exe"], startupinfo=startupinfo, shell=True)
    else:
        os.system("killall librespot")


def get_token(librespot):
    # get authentication token for api - prefer cached version
    token_info = None
    try:
        if librespot.playback_supported:
            # try to get a token with librespot
            token_info = request_token_librespot(librespot)
        else:
            # request new token with web flow
            token_info = request_token_web(librespot.username)
    except Exception as exc:
        log_msg("Couldn't request authentication token. Username/password error ?")
        log_exception("utils.get_token", exc)
        token_info = None
    return token_info


def request_token_librespot(librespot):
    '''request token by using the librespot binary'''
    token_info = None
    if librespot.playback_supported:
        try:
            args = ["-t", "--client-id", CLIENTID, "--scope", ",".join(SCOPE), "-n", "temp"]
            librespot = librespot.run_librespot(arguments=args)
            stdout, stderr = librespot.communicate()
            result = None
            log_msg(stdout, xbmc.LOGDEBUG)
            for line in stdout.split():
                line = line.strip()
                if line.startswith("{\"accessToken\""):
                    result = eval(line)
            # transform token info to spotipy compatible format
            if result:
                token_info = {}
                token_info["access_token"] = result["accessToken"]
                token_info["expires_in"] = result["expiresIn"]
                token_info["token_type"] = result["tokenType"]
                token_info["scope"] = ' '.join(result["scope"])
                token_info['expires_at'] = int(time.time()) + token_info['expires_in']
                token_info['refresh_token'] = result["accessToken"]
                log_msg("Token from librespot: %s" % token_info, xbmc.LOGDEBUG)
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


def parse_spotify_track(track, is_album_track=True, is_remote=False):
    if "track" in track:
        track = track['track']
    if track.get("images"):
        thumb = track["images"][0]['url']
    elif track['album'].get("images"):
        thumb = track['album']["images"][0]['url']
    else:
        thumb = ""
    duration = track['duration_ms']/1000
    
    if is_remote:
        url = "http://localhost:%s/silence/%s" % (PROXY_PORT, duration)
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
        "duration": duration
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
    

def get_playername():
    playername = xbmc.getInfoLabel("System.FriendlyName").decode("utf-8")
    if playername == "Kodi":
        import socket
        playername = "Kodi (%s)" % socket.gethostname()
    return playername


class LibreSpot(object):
    '''
        librespot is wrapped into a seperate class to store common properties
        this is done to prevent hitting a kodi issue where calling one of the infolabel methods
        at playback time causes a crash of the playback
    '''
    username = None
    password = None
    playback_supported = False
    playername = None
    supports_discovery = True
    buffer_track = False
    __librespot_binary = None
    __cache_path = None

    def __init__(self):
        '''initialize with default values'''
        addon = xbmcaddon.Addon(id=ADDON_ID)
        self.username = addon.getSetting("username").decode("utf-8")
        self.password = addon.getSetting("password").decode("utf-8")
        self.buffer_track = addon.getSetting("buffer_track").decode("utf-8") == "true"
        if addon.getSetting("cache_path").decode("utf-8") == "true":
            cache_path = xbmc.translatePath(addon.getSetting("cache_path")).decode("utf-8")
            if os.path.isdir(cache_path):
                self.__cache_path = cache_path
        del addon
        self.playername = get_playername()
        self.__librespot_binary = self.get_librespot_binary()
        if self.__librespot_binary:
            # perform self check
            args = ["--backend", "?"]
            librespot = self.run_librespot(arguments=args, self_check=True)
            stdout, stderr = librespot.communicate()
            log_msg(stdout)
            if "Available Backends" in stdout:
                self.playback_supported = True
                xbmc.executebuiltin("SetProperty(spotify.supportsplayback, true, Home)")
            else:
                log_msg("Error while verifying librespot. Local playback is disabled.")

    def run_librespot(self, arguments=None, self_check=False):
        '''On supported platforms we include librespot binary'''
        if self.playback_supported or self_check:
            try:
                args = [
                    self.__librespot_binary,
                    "-u", self.username,
                    "-p", self.password,
                    "-b", "320" # force bitrate to highest quality
                ]
                if arguments:
                    args += arguments
                if not "-n" in args:
                    args += ["-n", self.playername]
                if self.__cache_path:
                    args += ["-c", self.__cache_path]
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
                my_env = os.environ.copy()
                my_env["DYLD_LIBRARY_PATH"] = os.path.dirname(self.__librespot_binary)
                my_env["LD_LIBRARY_PATH"] = os.path.dirname(self.__librespot_binary)
                return subprocess.Popen(args, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, env=my_env)
            except Exception as exc:
                log_exception(__name__, exc)
        return None

    def get_librespot_binary(self):
        '''find the correct librespot binary belonging to the platform'''
        sp_binary = None
        if xbmc.getCondVisibility("System.Platform.Windows"):
            if os.path.isdir("c:\\Program Files (x86)"):
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "windows_x86_64", "librespot.exe")
            else:
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "windows_i686", "librespot.exe")
            self.supports_discovery = False # The current MDNS implementation cannot be built on Windows
        elif xbmc.getCondVisibility("System.Platform.OSX"):
            # macos binary is x86_64 intel
            sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "darwin_x86_64", "librespot")
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            # try to find out the correct architecture by trial and error
            import platform
            architecture = platform.machine()
            if architecture.startswith('AMD64') or architecture.startswith('x86_64'):
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "linux_x86_64", "librespot")
            elif architecture.startswith('aarch64'): # todo: what if we're running 32bit OS on aarch64 ?
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "linux_aarch64", "librespot")
            elif os.path.isdir("/lib/arm-linux-gnueabihf/") or xbmc.getCondVisibility("System.Platform.Linux.RaspberryPi"): # I didn't know any other valid way of detecting armhf support
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "linux_armhf", "librespot")
            elif architecture.startswith('arm'):
                sp_binary = os.path.join(os.path.dirname(__file__), "librespot", "linux_arm", "librespot")
        if sp_binary:
            st = os.stat(sp_binary)
            os.chmod(sp_binary, st.st_mode | stat.S_IEXEC)
            log_msg("Architecture detected. Using librespot binary %s" % sp_binary)
        else:
            log_msg("Failed to detect architecture or platform not supported ! Local playback will not be available.")
        return sp_binary
