import ctypes

#Import general classes from the high level module
import spotify

#Also import this one's siblings
from spotify import user, handle_sp_error, playlistcontainer, playlist

#Import low level api
from _spotify import playlistcontainer as _playlistcontainer, user as _user, session as _session, is_linux

#Decorators
from spotify.utils.decorators import synchronized

from spotify.utils.weakmethod import WeakMethod

import weakref



class ProxySessionCallbacks:
    __session = None
    __callbacks = None
    __manager = None
    __struct = None
    
    
    def __init__(self, session, callbacks, manager):
        self.__session = weakref.proxy(session)
        self.__callbacks = callbacks
        self.__manager = manager
        self.__struct = _session.callbacks(
            _session.cb_logged_in(WeakMethod(self._logged_in)),
            _session.cb_logged_out(WeakMethod(self._logged_out)),
            _session.cb_metadata_updated(WeakMethod(self._metadata_updated)),
            _session.cb_connection_error(WeakMethod(self._connection_error)),
            _session.cb_message_to_user(WeakMethod(self._message_to_user)),
            _session.cb_notify_main_thread(WeakMethod(self._notify_main_thread)),
            _session.cb_music_delivery(WeakMethod(self._music_delivery)),
            _session.cb_play_token_lost(WeakMethod(self._play_token_lost)),
            _session.cb_log_message(WeakMethod(self._log_message)),
            _session.cb_end_of_track(WeakMethod(self._end_of_track)),
            _session.cb_streaming_error(WeakMethod(self._streaming_error)),
            _session.cb_userinfo_updated(WeakMethod(self._userinfo_updated)),
            _session.cb_start_playback(WeakMethod(self._start_playback)),
            _session.cb_stop_playback(WeakMethod(self._stop_playback)),
            _session.cb_get_audio_buffer_stats(WeakMethod(self._get_audio_buffer_stats)),
            _session.cb_offline_status_updated(WeakMethod(self._offline_status_updated)),
            _session.cb_offline_error(WeakMethod(self._offline_error)),
            _session.cb_credentials_blob_updated(WeakMethod(self._credentials_blob_updated)),
            _session.cb_connectionstate_updated(WeakMethod(self._connectionstate_updated)),
            _session.cb_scrobble_error(WeakMethod(self._scrobble_error)),
            _session.cb_private_session_mode_changed(WeakMethod(self._private_session_mode_changed)),
        )
    
    
    def _logged_in(self, session, error):
        self.__callbacks.logged_in(self.__session, error)
        self.__manager.logged_in(self.__session, error)
    
    
    def _logged_out(self, session):
        self.__callbacks.logged_out(self.__session)
        self.__manager.logged_out(self.__session)
    
    
    def _metadata_updated(self, session):
        self.__callbacks.metadata_updated(self.__session)
        self.__manager.metadata_updated(self.__session)
    
    
    def _connection_error(self, session, error):
        self.__callbacks.connection_error(self.__session, error)
        self.__manager.connection_error(self.__session, error)
    
    
    def _message_to_user(self, session, message):
        self.__callbacks.message_to_user(self.__session, message)
        self.__manager.message_to_user(self.__session, message)
    
    
    def _notify_main_thread(self, session):
        self.__callbacks.notify_main_thread(self.__session)
        self.__manager.notify_main_thread(self.__session)
    
    
    def get_frame_data_size(self, format, num_frames):
        if format.sample_type == spotify.SampleType.Int16NativeEndian:
            frame_size = format.channels * 2
        
        else:
            frame_size = -1
        
        return frame_size * num_frames
    
    
    def _music_delivery(self, session, format_p, frames, num_frames):
        format = format_p.contents
        size = self.get_frame_data_size(format, num_frames)
        dest = ctypes.cast(frames, ctypes.POINTER(ctypes.c_char * size))
        data = str(buffer(dest.contents))
        
        return self.__callbacks.music_delivery(
            self.__session, data, num_frames,
            format.sample_type, format.sample_rate, format.channels
        )
    
    
    def _play_token_lost(self, session):
        self.__callbacks.play_token_lost(self.__session)
        self.__manager.play_token_lost(self.__session)
    
    
    def _log_message(self, session, data):
        self.__callbacks.log_message(self.__session, data)
        self.__manager.log_message(self.__session, data)
    
    
    def _end_of_track(self, session):
        self.__callbacks.end_of_track(self.__session)
        self.__manager.end_of_track(self.__session)
    
    
    def _streaming_error(self, session, error):
        self.__callbacks.streaming_error(self.__session, error)
        self.__manager.streaming_error(self.__session, error)
    
    
    def _userinfo_updated(self, session):
        self.__callbacks.userinfo_updated(self.__session)
        self.__manager.userinfo_updated(self.__session)
    
    
    def _start_playback(self, session):
        self.__callbacks.start_playback(self.__session)
        self.__manager.start_playback(self.__session)
    
    
    def _stop_playback(self, session):
        self.__callbacks.stop_playback(self.__session)
        self.__manager.stop_playback(self.__session)
    
    
    def _get_audio_buffer_stats(self, session, stats_p):
        st = stats_p.contents
        res = self.__callbacks.get_audio_buffer_stats(self.__session)
        if res is not None:
            st.samples, st.stutter = res 
    
    
    def _offline_status_updated(self, session):
        self.__callbacks.offline_status_updated(self.__session)
        self.__manager.offline_status_updated(self.__session)
    
    
    def _offline_error(self, session, error):
        self.__callbacks.offline_error(self.__session, error)
        self.__manager.offline_error(self.__session, error)
    
    
    def _credentials_blob_updated(self, session, blob):
        self.__callbacks.credentials_blob_updated(self.__session, blob)
        self.__manager.credentials_blob_updated(self.__session, blob)
    
    
    def _connectionstate_updated(self, session):
        self.__callbacks.connectionstate_updated(self.__session)
        self.__manager.connectionstate_updated(self.__session)
    
    
    def _scrobble_error(self, session, error):
        self.__callbacks.scrobble_error(self.__session, error)
        self.__manager.scrobble_error(self.__session, error)
    
    
    def _private_session_mode_changed(self, session, is_private):
        self.__callbacks.private_session_mode_changed(self.__session, is_private)
        self.__manager.private_session_mode_changed(self.__session, is_private)
    
    
    def get_callback_struct(self):
        return self.__struct



class SessionCallbacks:
    def logged_in(self, session, error):
        pass
    
    def logged_out(self, session):
        pass
    
    def metadata_updated(self, session):
        pass
    
    def connection_error(self, session, error):
        pass
    
    def message_to_user(self, session, message):
        pass
    
    def notify_main_thread(self, session):
        pass
    
    def music_delivery(self, session, frames, num_frames, sample_type, sample_rate, channels):
        pass
    
    def play_token_lost(self, session):
        pass
    
    def log_message(self, session, message):
        pass
    
    def end_of_track(self, session):
        pass
    
    def streaming_error(self, session, error):
        pass
    
    def userinfo_updated(self, session):
        pass
    
    def start_playback(self, session):
        pass
    
    def stop_playback(self, session):
        pass
    
    def get_audio_buffer_stats(self, session):
        pass
    
    def offline_status_updated(self, session):
        pass
    
    def offline_error(self, session, error):
        pass
    
    def credentials_blob_updated(self, session, blob):
        pass
    
    def connectionstate_updated(self, session):
        pass
    
    def scrobble_error(self, session, error):
        pass
    
    def private_session_mode_changed(self, session, is_private):
        pass



#classes
class Session:
    api_version = 12
    
    __session_struct = None
    __session_interface = None
    
    __proxy_callbacks = None
    __callback_manager = None
    
    _user_callbacks = None
    _metadata_callbacks = None
    
    
    def __init__(self, callbacks, cache_location="", settings_location="", app_key=None, user_agent=None, compress_playlists=False, dont_save_metadata_for_playlists=False, initially_unload_playlists=False, device_id=None, proxy=None, proxy_username=None, proxy_password=None, ca_certs_filename=None, tracefile=None):
        #Low level interface
        self.__session_interface = _session.SessionInterface()
        
        #Callback managers
        self._user_callbacks = spotify.CallbackQueueManager()
        self._metadata_callbacks = spotify.CallbackQueueManager()
        
        #prepare callbacks
        self.__callback_manager = spotify.CallbackManager()
        self.__callbacks = ProxySessionCallbacks(
            self, callbacks, self.__callback_manager
        )
        
        #app key conversion
        appkey_c = (ctypes.c_byte * len(app_key))(*app_key)
        
        args = [
            self.api_version,
            cache_location,
            settings_location,
            appkey_c,
            ctypes.sizeof(appkey_c),
            user_agent,
            ctypes.pointer(self.__callbacks.get_callback_struct()),
            ctypes.c_void_p(),
            compress_playlists,
            dont_save_metadata_for_playlists,
            initially_unload_playlists,
            device_id,
            proxy,
            proxy_username,
            proxy_password,
            tracefile,
        ]
        
        #Linux builds have an extra member just before tracefile
        if is_linux():
            args.insert(-1, ca_certs_filename)
        
        #initialize app config
        config = _session.config(*args)
        
        self.__session_struct = ctypes.c_void_p()
        err = self.__session_interface.create(ctypes.byref(config), ctypes.byref(self.__session_struct))
        spotify.handle_sp_error(err)
    
    
    def add_callbacks(self, callbacks):
        self.__callback_manager.add_callbacks(callbacks)
    
    
    def remove_callbacks(self, callbacks):
        self.__callback_manager.remove_callbacks(callbacks)
    
    
    @synchronized
    def login(self, username, password, remember_me=False, blob=None):
        self.__session_interface.login(
            self.__session_struct, username, password, remember_me, blob
        )
    
    
    @synchronized
    def relogin(self):
        handle_sp_error(
            self.__session_interface.relogin(self.__session_struct)
        )
    
    
    @synchronized
    def remembered_user(self):
        buf = (ctypes.c_char * 255)()
        res = self.__session_interface.remembered_user(
            self.__session_struct, buf, ctypes.sizeof(buf)
        )
        if res != -1:
            return buf.value
    
    
    @synchronized
    def user_name(self):
        return self.__session_interface.user_name(self.__session_struct)
    
    
    @synchronized
    def forget_me(self):
        self.__session_interface.forget_me(self.__session_struct)
        
    
    @synchronized
    def user(self, onload=None):
        user_struct = self.__session_interface.user(self.__session_struct)
        
        if user_struct is not None:
            ui = _user.UserInterface()
            ui.add_ref(user_struct)
            user_obj = user.User(user_struct)
                
            if onload != None:
                self._user_callbacks.add_callback(
                    user_obj.is_loaded, onload, user_obj
                )
                    
            return user_obj
    
    
    @synchronized
    def logout(self):
        self.__session_interface.logout(self.__session_struct)
    
    
    @synchronized
    def flush_caches(self):
        self.__session_interface.flush_caches(self.__session_struct)
    
    
    @synchronized
    def connectionstate(self):
        return self.__session_interface.connectionstate(self.__session_struct)
    
    
    @synchronized
    def userdata(self):
        return self.__session_interface.userdata(self.__session_struct)
    
    
    @synchronized
    def set_cache_size(self, size):
        self.__session_interface.set_cache_size(self.__session_struct, size)
    
    
    @synchronized
    def process_events(self):
        next_timeout = ctypes.c_int(0)
        self.__session_interface.process_events(
            self.__session_struct, ctypes.byref(next_timeout)
        )
        
        return next_timeout.value / 1000.0
        
    
    @synchronized
    def player_load(self, track):
        handle_sp_error(
            self.__session_interface.player_load(
                self.__session_struct, track.get_struct()
            )
        )
    
    
    @synchronized
    def player_seek(self, offset):
        self.__session_interface.player_seek(self.__session_struct, offset)
    
    
    @synchronized
    def player_play(self, play):
        self.__session_interface.player_play(self.__session_struct, play)
    
    
    @synchronized
    def player_unload(self):
        self.__session_interface.player_unload(self.__session_struct)
    
    
    @synchronized
    def player_prefetch(self, track):
        handle_sp_error(
            self.__session_interface.player_prefetch(
                self.__session_struct, track.get_struct()
            )
        )
    
    
    @synchronized
    def playlistcontainer(self):
        container_struct = self.__session_interface.playlistcontainer(
            self.__session_struct
        )
        
        if container_struct is not None:
            pi = _playlistcontainer.PlaylistContainerInterface()
            pi.add_ref(container_struct)
            return playlistcontainer.PlaylistContainer(container_struct)
    
    
    @synchronized
    def inbox_create(self):
        return playlist.Playlist(
            self.__session_interface.inbox_create(self.__session_struct)
        )
    
    
    @synchronized
    def starred_create(self):
        return playlist.Playlist(
            self.__session_interface.starred_create(self.__session_struct)
        )
    
    
    @synchronized
    def starred_for_user_create(self, canonical_username):
        return playlist.Playlist(
            self.__session_interface.starred_for_user_create(
                self.__session_struct, canonical_username
            )
        )
    
    
    @synchronized
    def publishedcontainer_for_user_create(self, canonical_username):
        return playlistcontainer.PlaylistContainer(
            self.__session_interface.publishedcontainer_for_user_create(
                self.__session_struct, canonical_username
            )
        )
    
    
    @synchronized
    def preferred_bitrate(self, bitrate):
        handle_sp_error(
            self.__session_interface.preferred_bitrate(
                self.__session_struct, bitrate
            )
        )
    
    
    @synchronized
    def preferred_offline_bitrate(self, bitrate, allow_resync):
        handle_sp_error(
            self.__session_interface.preferred_offline_bitrate(
                self.__session_struct, bitrate, allow_resync
            )
        )
    
    
    @synchronized
    def get_volume_normalization(self):
        return self.__session_interface.get_volume_normalization(
            self.__session_struct
        )
    
    
    @synchronized
    def set_volume_normalization(self, on):
        self.__session_interface.set_volume_normalization(
            self.__session_struct, on
        )
    
    
    @synchronized
    def set_private_session(self, enabled):
        self.__session_interface.set_private_session(
            self.__session_struct, enabled
        )
    
    
    @synchronized
    def is_private_session(self):
        return self.__session_interface.is_private_session(
            self.__session_struct
        )
    
    
    @synchronized
    def set_scrobbling(self, provider, state):
        handle_sp_error(
            self.__session_interface.set_scrobbling(
                self.__session_struct, provider, state
            )
        )
    
    
    @synchronized
    def set_connection_type(self, conn_type):
        self.__session_interface.set_connection_type(
            self.__session_struct, conn_type
        )
    
    
    @synchronized
    def is_scrobbling(self, provider):
        state = None
        handle_sp_error(
            self.__session_interface.is_scrobbling(
                self.__session_struct, provider, state
            )
        )
        
        return state
    
    
    @synchronized
    def is_scrobbling_possible(self, provider):
        out = None
        handle_sp_error(
            self.__session_interface.is_scrobbling_possible(
                self.__session_struc, provider, out
            )
        )
        
        return out
    
    
    @synchronized
    def set_social_credentials(self, provider, username, password):
        handle_sp_error(
            self.__session_interface.set_social_credentials(
                self.__session_struct, provider, username, password
            )
        )
    
    
    @synchronized
    def set_connection_rules(self, conn_rules):
        self.__session_interface.set_connection_rules(
            self.__session_struct, conn_rules
        )
    
    
    @synchronized
    def offline_tracks_to_sync(self):
        return self.__session_interface.offline_tracks_to_sync(
            self.__session_struct
        )
    
    
    @synchronized
    def offline_num_playlists(self):
        return self.__session_interface.offline_num_playlists(
            self.__session_struct
        )
    
    
    @synchronized
    def offline_sync_get_status(self):
        sync_struct = _session.offline_sync_status()
        status = self.__session_interface.offline_sync_get_status(
            self.__session_struct, ctypes.byref(sync_struct)
        )
        
        if status:
            return{
                'queued_tracks': sync_struct.queued_tracks,
                'queued_bytes': sync_struct.queued_bytes,
                'done_tracks': sync_struct.done_tracks,
                'done_bytes': sync_struct.done_bytes,
                'copied_tracks': sync_struct.copied_tracks,
                'copied_bytes': sync_struct.copied_bytes,
                'willnotcopy_tracks': sync_struct.willnotcopy_tracks,
                'error_tracks': sync_struct.error_tracks,
                'syncing': sync_struct.syncing,
            }
    
    
    @synchronized
    def offline_time_left(self):
        return self.__session_interface.offline_time_left(
            self.__session_struct
        )
    
    
    @synchronized
    def user_country(self):
        return self.__session_interface.user_country(
            self.__session_struct
        )
    
    
    @synchronized
    def get_struct(self):
        return self.__session_struct
    
    
    @synchronized
    def __del__(self):
        self.__session_interface.release(self.__session_struct)
