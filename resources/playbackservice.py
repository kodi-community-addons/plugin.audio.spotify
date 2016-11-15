# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
import os, os.path
import xbmc, xbmcgui
import threading
import weakref
import re
import traceback
from utils import *
load_all_libraries()
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
        logMsg('logged in: {0:d}'.format(error_num))
        self.__app.set_var('login_last_error', error_num)
        if error_num != ErrorType.Ok:
            self.__app.get_var('connstate_event').set()

    def logged_out(self, session):
        logMsg('logged out')
        self.__app.get_var('logout_event').set()

    def connection_error(self, session, error):
        logMsg('connection error: {0:d}'.format(error))

    def message_to_user(self, session, data):
        logMsg('message to user: {0}'.format(data))

    def log_message(self, session, data):
        logMsg("Spotify Callbacks: %s" %data, True)
        pass

    def streaming_error(self, session, error):
        logMsg('streaming error: {0:d}'.format(error))

    def play_token_lost(self, session):
        self.__audio_buffer.stop()
        #Only stop if we're actually playing spotify content
        if xbmc.getInfoLabel("MusicPlayer.(0).Property(spotifytrackid)"):
            xbmc.executebuiltin('PlayerControl(stop)')

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
    session.set_volume_normalization(True)

def do_login(session, app):
    #Get the last error if we have one
    if app.has_var('login_last_error'):
        prev_error = app.get_var('login_last_error')
    else:
        prev_error = 0

    #Get login details from settings
    username = SETTING("username").decode("utf-8")
    password = SETTING("password").decode("utf-8")

    #If no previous errors and we have a remembered user
    logMsg('Checking remembered_user ..')
    if prev_error == 0 and try_decode(session.remembered_user()) == username:
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

def get_next_track(sess_obj):
    next_trackid = xbmc.getInfoLabel("MusicPlayer.(1).Property(spotifytrackid)")
    if next_trackid:
        #Try loading it as a spotify track
        link_obj = link.create_from_string("spotify:track:%s" %next_trackid)
        if link_obj:
            return load_track(sess_obj, link_obj.as_track())

        #Try to parse as a local track
        link_obj = link.create_from_string("spotify:local:%s" %next_trackid)
        if link_obj:
            local_track = link_obj.as_track()
            return load_track(sess_obj, local_track.get_playable(sess_obj))
    else: return None

def get_preloader_callback(session, buffer):
    session = weakref.proxy(session)
    def preloader():
        next_track = get_next_track(session)
        if next_track:
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
            preloader_cb = get_preloader_callback(sess, buf)
            logMsg('Setting callback ..')
            proxy_runner.set_stream_end_callback(preloader_cb)

            user_agent = try_decode('Spotify/{0} (XBMC/{1})'.format(ADDON_VERSION, xbmc.getInfoLabel("System.BuildVersion"))).decode('utf-8', 'ignore')
            logMsg('Obtaining user token ..')
            playtoken = proxy_runner.get_user_token(user_agent)
            header_dict = {
                'User-Agent': user_agent,
                'x-csrf-token': playtoken
                }
            logMsg('Encoding header ..')
            url_headers = urlencode(header_dict)
            WINDOW.setProperty("Spotify.PlayToken",url_headers)
            WINDOW.setProperty("Spotify.PlayServer","%s:%s" %(proxy_runner.get_host(),proxy_runner.get_port()))
            WINDOW.setProperty("Spotify.ServiceReady","ready")

            #wait untill abortrequested
            while not app.get_var('exit_requested'):
                if monitor.abortRequested() or xbmc.abortRequested:
                    logMsg("Shutdown requested!")
                    app.set_var('exit_requested', True)
                monitor.waitForAbort(0.5)
            logMsg("Shutting down background processing...")

            #Playback and proxy deinit sequence
            xbmc.executebuiltin('PlayerControl(stop)')
            logMsg('Clearing stream / stopping ..')
            proxy_runner.clear_stream_end_callback()
            proxy_runner.stop()
            buf.cleanup()

            #Clear some vars and collect garbage
            proxy_runner = None
            preloader_cb = None

            #Logout
            logMsg('Logging out ..')
            if sess.user():
                sess.logout()
                logout_event.wait(2)

        #Stop main loop
        error = login_get_last_error(app)
        WINDOW.setProperty("Spotify.LastError",str(login_get_last_error(app)))
        ml_runner.stop()

    except (Exception) as ex:
        if str(ex) != '':
            # trace = traceback.format_exc()
            logMsg("TRACE: " + ( ''.join(traceback.format_stack()) ) )
            logMsg("EXCEPTION in background service: " + str(ex))
            # logMsg("STACK: %s" %trace, True)
            if "Unable to find" in str(ex):
                WINDOW.setProperty("Spotify.LastError","999")
            else:
                error = str(ex)
                WINDOW.clearProperty("Spotify.ServiceReady")
                WINDOW.setProperty("Spotify.LastError",error)
