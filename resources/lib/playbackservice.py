#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import os.path
import xbmc
import xbmcgui
import threading
import gc
import traceback
import weakref
import re
import playback
from spotify import MainLoop, ConnectionState, ErrorType, Bitrate, link
from spotify import track as _track
from spotify.utils.loaders import load_track, load_albumbrowse
from spotify.session import Session, SessionCallbacks
from spotifyproxy.httpproxy import ProxyRunner
from spotifyproxy.audio import BufferManager
from taskutils.decorators import run_in_thread
from taskutils.threads import TaskManager
from threading import Event
from utils import SettingsManager, CacheManagement, StreamQuality, \
    GuiSettingsReader, logMsg, set_dll_paths, appkey
from __main__ import ADDON_VERSION, ADDON_PATH,SETTING,WINDOW,SAVESETTING
from logs import get_logger, setup_logging

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

#Cross python version import of urlencode
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

class Application:
    __vars = None

    def __init__(self):
        self.__vars = {}

    def set_var(self, name, value):
        self.__vars[name] = value

    def has_var(self, name):
        return name in self.__vars

    def get_var(self, name):
        return self.__vars[name]

    def remove_var(self, name):
        del self.__vars[name]


class Callbacks(SessionCallbacks):
    __mainloop = None
    __audio_buffer = None
    __logout_event = None
    __app = None
    __logger = None
    __log_regex = None

    def __init__(self, mainloop, audio_buffer, app):
        self.__mainloop = mainloop
        self.__audio_buffer = audio_buffer
        self.__app = app
        self.__logger = get_logger()
        self.__log_regex = re.compile('[0-9]{2}:[0-9]{2}:[0-9]{2}'
                                      '\.[0-9]{3}\s(W|I|E)\s')

    def logged_in(self, session, error_num):
        #Log this event
        self.__logger.debug('logged in: {0:d}'.format(error_num))

        #Store last error code
        self.__app.set_var('login_last_error', error_num)

        #Take action if error status is not ok
        if error_num != ErrorType.Ok:
            self.__app.get_var('connstate_event').set()

    def logged_out(self, session):
        self.__logger.debug('logged out')
        self.__app.get_var('logout_event').set()

    def connection_error(self, session, error):
        self.__logger.error('connection error: {0:d}'.format(error))

    def message_to_user(self, session, data):
        self.__logger.info('message to user: {0}'.format(data))

    def _get_log_message_level(self, message):
        matches = self.__log_regex.match(message)
        if matches:
            return matches.group(1)

    def log_message(self, session, data):
        message_level = self._get_log_message_level(data)
        if message_level == 'I':
            self.__logger.info(data)
        elif message_level == 'W':
            self.__logger.warning(data)
        else:
            self.__logger.error(data)

    def streaming_error(self, session, error):
        self.__logger.info('streaming error: {0:d}'.format(error))

    @run_in_thread
    def play_token_lost(self, session):

        #Cancel the current buffer
        self.__audio_buffer.stop()

        if self.__app.has_var('playlist_manager'):
            self.__app.get_var('playlist_manager').stop(False)

        dlg = xbmcgui.Dialog()
        dlg.ok('Playback stopped', 'This account is in use on another device.')

    def end_of_track(self, session):
        self.__audio_buffer.set_track_ended()

    def notify_main_thread(self, session):
        self.__mainloop.notify()

    def music_delivery(self, session, data, num_samples, sample_type,
                       sample_rate, num_channels):
        return self.__audio_buffer.music_delivery(
            data, num_samples, sample_type, sample_rate, num_channels)

    def connectionstate_changed(self, session):

        #Set the apropiate event flag, if available
        self.__app.get_var('connstate_event').set()
        
    def search_complete(self, result):
        print("search complete")


class MainLoopRunner(threading.Thread):
    __mainloop = None
    __session = None
    __proxy = None

    def __init__(self, mainloop, session):
        threading.Thread.__init__(self)
        self.__mainloop = mainloop
        self.__session = weakref.proxy(session)

    def run(self):
        self.__mainloop.loop(self.__session)

    def stop(self):
        self.__mainloop.quit()
        self.join(10)


def get_audio_buffer_size():
    #Base buffer setting will be 10s
    buffer_size = 10

    try:
        reader = GuiSettingsReader()
        value = reader.get_setting('settings.musicplayer.crossfade')
        buffer_size += int(value)

    except:
        xbmc.log(
            'Failed reading crossfade setting. Using default value.',
            xbmc.LOGERROR
        )

    return buffer_size


def check_dirs():
    addon_data_dir = os.path.join(
        xbmc.translatePath('special://profile/addon_data'),
        'plugin.audio.spotify'
    )

    #Auto-create profile dir if it does not exist
    if not os.path.exists(addon_data_dir):
        os.makedirs(addon_data_dir)

    #Libspotify cache & settings
    sp_cache_dir = os.path.join(addon_data_dir, 'libspotify/cache')
    sp_settings_dir = os.path.join(addon_data_dir, 'libspotify/settings')

    if not os.path.exists(sp_cache_dir):
        os.makedirs(sp_cache_dir)

    if not os.path.exists(sp_settings_dir):
        os.makedirs(sp_settings_dir)

    return (addon_data_dir, sp_cache_dir, sp_settings_dir)


def set_settings(settings_obj, session):
    #If cache is enabled set the following one
    if settings_obj.get_cache_status():
        if settings_obj.get_cache_management() == CacheManagement.Manual:
            cache_size_mb = settings_obj.get_cache_size() * 1024
            session.set_cache_size(cache_size_mb)

    #Bitrate config
    br_map = {
        StreamQuality.Low: Bitrate.Rate96k,
        StreamQuality.Medium: Bitrate.Rate160k,
        StreamQuality.High: Bitrate.Rate320k,
    }
    session.preferred_bitrate(br_map[settings_obj.get_audio_quality()])

    #And volume normalization
    session.set_volume_normalization(settings_obj.get_audio_normalize())


def do_login(session, app):
    #Get the last error if we have one
    if app.has_var('login_last_error'):
        prev_error = app.get_var('login_last_error')
    else:
        prev_error = 0
        
    #Get login details from settings
    username = SETTING("username")
    password = SETTING("password")

    #If no previous errors and we have a remembered user
    if prev_error == 0 and session.remembered_user() == username:
        session.relogin()
        status = True
        logMsg( "Cached session found" )
    else:
        
        if not username or not password:
            kb = xbmc.Keyboard('', "Enter username")
            kb.setHiddenInput(False)
            kb.doModal()
            if kb.isConfirmed():
                value = kb.getText()
                username = value
                
                #also set password
                kb = xbmc.Keyboard('', "Enter password")
                kb.setHiddenInput(True)
                kb.doModal()
                if kb.isConfirmed():
                    value = kb.getText()
                    password = value
                    
                    SAVESETTING("username",username)
                    SAVESETTING("password",password)
                
        #do login
        session.login(username, password, True)

    return session


def login_get_last_error(app):
    if app.has_var('login_last_error'):
        return app.get_var('login_last_error')
    else:
        return 0

def wait_for_connstate(session, app, state):

    #Store the previous login error number
    last_login_error = login_get_last_error(app)

    #Add a shortcut to the connstate event
    cs = app.get_var('connstate_event')

    #Wrap all the tests for the following loop
    def continue_loop():

        #Get the current login error
        cur_login_error = login_get_last_error(app)

        #Continue the loop while these conditions are met:
        #  * An exit was not requested
        #  * Connection state was not the desired one
        #  * No login errors where detected
        return (
            not app.get_var('exit_requested') and
            session.connectionstate() != state and (
                last_login_error == cur_login_error or
                cur_login_error == ErrorType.Ok
            )
        )

    #Keep testing until conditions are met
    while continue_loop():
        cs.wait(5)
        cs.clear()

    return session.connectionstate() == state

def get_preloader_callback(session, playlist_manager, buffer):
    session = weakref.proxy(session)

    def preloader():
        next_track = playlist_manager.get_next_item(session)
        if next_track is not None:
            ta = next_track.get_availability(session)
            if ta == _track.TrackAvailability.Available:
                buffer.open(session, next_track)

    return preloader

def main():
    setup_logging()
    set_dll_paths('resources/lib/libspotify/dlls')
    #Surround the rest of the init process
    try:

        #And perform the rest of the import statements
        from _spotify import unload_library
        
        #Initialize app var storage
        app = Application()
        logout_event = Event()
        connstate_event = Event()
        app.set_var('logout_event', logout_event)
        app.set_var('login_last_error', ErrorType.Ok)
        app.set_var('connstate_event', connstate_event)
        app.set_var('exit_requested', False)

        #Check needed directories first
        data_dir, cache_dir, settings_dir = check_dirs()

        #Instantiate the settings obj
        settings_obj = SettingsManager()

        #Don't set cache folder if it's disabled
        if not settings_obj.get_cache_status():
            cache_dir = ''

        #Initialize spotify stuff
        ml = MainLoop()
        buf = BufferManager(get_audio_buffer_size())
        callbacks = Callbacks(ml, buf, app)
        sess = Session(
            callbacks,
            app_key=appkey,
            user_agent="python ctypes bindings",
            settings_location=settings_dir,
            cache_location=cache_dir,
            initially_unload_playlists=False
        )
        
        #Now that we have a session, set settings
        set_settings(settings_obj, sess)

        #Initialize libspotify's main loop handler on a separate thread
        ml_runner = MainLoopRunner(ml, sess)
        ml_runner.start()

        #Set the exit flag if login was cancelled
        if not do_login(sess, app):
            WINDOW.setProperty("Spotify.ServiceReady","error")
            app.set_var('exit_requested', True)
        elif wait_for_connstate(sess, app, ConnectionState.LoggedIn):
            
            proxy_runner = ProxyRunner(sess, buf, host='127.0.0.1', allow_ranges=True)
            proxy_runner.start()
            logMsg('starting proxy at port {0}'.format(proxy_runner.get_port()) )

            #Instantiate the playlist manager
            playlist_manager = playback.PlaylistManager(proxy_runner)
            app.set_var('playlist_manager', playlist_manager)
            preloader_cb = get_preloader_callback(sess, playlist_manager, buf)
            proxy_runner.set_stream_end_callback(preloader_cb)
            
            WINDOW.setProperty("Spotify.ServiceReady","ready")

            #wait untill abortrequested
            while not xbmc.Monitor().abortRequested() and not app.get_var('exit_requested'):
                trackids = WINDOW.getProperty("Spotify.PlayTrack").decode("utf-8")
                albumid = WINDOW.getProperty("Spotify.PlayAlbum").decode("utf-8")
                offsetstr = WINDOW.getProperty("Spotify.PlayOffset").decode("utf-8")
                if offsetstr: offset = int(offsetstr)
                else: offset = 0
                if trackids:
                    WINDOW.clearProperty("Spotify.PlayTrack")
                    tracks = []
                    for trackid in trackids.split(","):
                        link_obj = link.create_from_string("spotify:track:%s"%trackid)
                        trackobj = load_track(sess, link_obj.as_track() )
                        tracks.append(trackobj)
                    playlist_manager.play(tracks, sess, offset)
                if albumid:
                    WINDOW.clearProperty("Spotify.PlayAlbum")
                    link_obj = link.create_from_string("spotify:album:%s"%albumid)
                    albumobj = load_albumbrowse( sess, link_obj.as_album() )
                    playlist_manager.play(albumobj.tracks(), sess, offset)
                else:
                    xbmc.sleep(500)

            #Playback and proxy deinit sequence
            proxy_runner.clear_stream_end_callback()
            playlist_manager.stop()
            proxy_runner.stop()
            buf.cleanup()

            #Join all the running tasks
            tm = TaskManager()
            tm.cancel_all()

            #Clear some vars and collect garbage
            proxy_runner = None
            preloader_cb = None
            playlist_manager = None
            mainwin = None
            app.remove_var('playlist_manager')
            gc.collect()

            #Logout
            if sess.user() is not None:
                sess.logout()
                logout_event.wait(10)

        #Stop main loop
        error = login_get_last_error(app)
        WINDOW.setProperty("Spotify.LastError",str(login_get_last_error(app)))
        ml_runner.stop()
        
        #Do a final garbage collection after main
        gc.collect()


    except (SystemExit, Exception) as ex:
        if str(ex) != '':
            dlg = xbmcgui.Dialog()
            dlg.ok(ex.__class__.__name__, str(ex))
            traceback.print_exc()

    finally:
        WINDOW.clearProperty("Spotify.ServiceReady")
        unload_library("libspotify")

