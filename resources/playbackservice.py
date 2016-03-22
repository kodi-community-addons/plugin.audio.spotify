# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
import os, os.path
import xbmc, xbmcgui
import threading
import weakref
import re
from utils import *
load_all_libraries()
import playback
from spotify import MainLoop, ConnectionState, ErrorType, Bitrate, link
from spotify import track as _track
from spotify.utils.loaders import load_track, load_albumbrowse
from spotify.session import Session, SessionCallbacks
from spotifyproxy.httpproxy import ProxyRunner
from spotifyproxy.audio import BufferManager
from threading import Event

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

    def __init__(self, mainloop, audio_buffer, app):
        self.__mainloop = mainloop
        self.__audio_buffer = audio_buffer
        self.__app = app

    def logged_in(self, session, error_num):
        logMsg('logged in: {0:d}'.format(error_num),True)
        self.__app.set_var('login_last_error', error_num)
        if error_num != ErrorType.Ok:
            self.__app.get_var('connstate_event').set()

    def logged_out(self, session):
        logMsg('logged out',True)
        self.__app.get_var('logout_event').set()

    def connection_error(self, session, error):
        logMsg('connection error: {0:d}'.format(error))

    def message_to_user(self, session, data):
        logMsg('message to user: {0}'.format(data))

    def log_message(self, session, data):
        #logMsg("Spotify Callbacks: " + data, True)
        pass

    def streaming_error(self, session, error):
        logMsg('streaming error: {0:d}'.format(error))

    def play_token_lost(self, session):
        self.__audio_buffer.stop()
        if self.__app.has_var('playlist_manager'):
            self.__app.get_var('playlist_manager').stop(False)

    def end_of_track(self, session):
        self.__audio_buffer.set_track_ended()

    def notify_main_thread(self, session):
        self.__mainloop.notify()

    def music_delivery(self, session, data, num_samples, sample_type, sample_rate, num_channels):
        return self.__audio_buffer.music_delivery( data, num_samples, sample_type, sample_rate, num_channels)

    def connectionstate_changed(self, session):
        self.__app.get_var('connstate_event').set()
        
    def search_complete(self, result):
        pass

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
        self.join(4)

def get_audio_buffer_size():
    buffer_size = 10
    try:
        crossfadevalue = getJSON('Settings.GetSettingValue', '{"setting":"musicplayer.crossfade"}')
        buffer_size += crossfadevalue.get("value")
    except:
        logMsg('Failed reading crossfade setting. Using default value.')
    return buffer_size

def set_settings(session):
    session.preferred_bitrate(Bitrate.Rate320k)
    session.set_volume_normalization(True)

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
        #do login with stored credentials
        session.login(username, password, True)
    return session

def login_get_last_error(app):
    if app.has_var('login_last_error'):
        return app.get_var('login_last_error')
    else:
        return 0

def wait_for_connstate(session, app, state):
    last_login_error = login_get_last_error(app)
    cs = app.get_var('connstate_event')

    def continue_loop():
        cur_login_error = login_get_last_error(app)
        return (
            not app.get_var('exit_requested') and
            session.connectionstate() != state and (
                last_login_error == cur_login_error or
                cur_login_error == ErrorType.Ok
            )
        )
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
    try:
        app = Application()
        logout_event = Event()
        connstate_event = Event()
        monitor = xbmc.Monitor()
        app.set_var('logout_event', logout_event)
        app.set_var('login_last_error', ErrorType.Ok)
        app.set_var('connstate_event', connstate_event)
        app.set_var('exit_requested', False)
        app.set_var('monitor', monitor)
        data_dir, cache_dir, settings_dir = check_dirs()

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
        set_settings(sess)

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
            while not app.get_var('exit_requested'):
                trackids = WINDOW.getProperty("Spotify.PlayTrack").decode("utf-8")
                albumid = WINDOW.getProperty("Spotify.PlayAlbum").decode("utf-8")
                offsetstr = WINDOW.getProperty("Spotify.PlayOffset").decode("utf-8")
                if offsetstr: offset = int(offsetstr)
                else: offset = 0
                if monitor.abortRequested() or xbmc.abortRequested:
                    logMsg("Shutdown requested!")
                    app.set_var('exit_requested', True)
                elif trackids:
                    WINDOW.clearProperty("Spotify.PlayTrack")
                    tracks = []
                    for trackid in trackids.split(","):
                        link_obj = link.create_from_string("spotify:track:%s"%trackid)
                        trackobj = load_track(sess, link_obj.as_track() )
                        tracks.append(trackobj)
                    playlist_manager.play(tracks, sess, offset)
                elif albumid:
                    WINDOW.clearProperty("Spotify.PlayAlbum")
                    link_obj = link.create_from_string("spotify:album:%s"%albumid)
                    albumobj = load_albumbrowse( sess, link_obj.as_album() )
                    playlist_manager.play(albumobj.tracks(), sess, offset)
                else:
                    monitor.waitForAbort(0.5)
            logMsg("Shutting down background processing...")

            #Playback and proxy deinit sequence
            proxy_runner.clear_stream_end_callback()
            playlist_manager.stop()
            proxy_runner.stop()
            buf.cleanup()

            #Clear some vars and collect garbage
            proxy_runner = None
            preloader_cb = None
            playlist_manager = None
            app.remove_var('playlist_manager')

            #Logout
            if sess.user() is not None:
                sess.logout()
                logout_event.wait(2)

        #Stop main loop
        error = login_get_last_error(app)
        WINDOW.setProperty("Spotify.LastError",str(login_get_last_error(app)))
        ml_runner.stop()

    except (Exception) as ex:
        if str(ex) != '':
            logMsg("ERROR in backgroundservice! " + str(ex))

    finally:
        WINDOW.clearProperty("Spotify.ServiceReady")
