__all__ = [
    "utils",
    "album", "albumbrowse", "artist", "artistbrowse",
    "image", "inbox", "link", "localtrack",
    "playlist", "playlistcontainer", "search",
    "session", "toplistbrowse", "track", "user",
]


import _spotify
import threading

from spotify.utils.decorators import synchronized



def handle_sp_error(errcode):
    if errcode != 0:
        iface = _spotify.SpotifyInterface()
        msg = iface.error_message(errcode)
        raise LibSpotifyError(msg)



def build_id():
    iface = _spotify.SpotifyInterface()
    return iface.build_id()



class LibSpotifyError(Exception):
    pass



class DuplicateCallbackError(LibSpotifyError):
    pass



class UnknownCallbackError(LibSpotifyError):
    pass



class ErrorType:
    Ok = 0
    BadApiVersion = 1
    ApiInitializationFailed = 2
    TrackNotPlayable = 3
    BadApplicationKey = 5
    BadUsernameOrPassword = 6
    UserBanned = 7
    UnableToContactServer = 8
    ClientTooOld = 9
    OtherPermanent = 10
    BadUserAgent = 11
    MissingCallback = 12
    InvalidIndata = 13
    IndexOutOfRange = 14
    UserNeedsPremium = 15
    OtherTransient = 16
    IsLoading = 17
    NoStreamAvailable = 18
    PermissionDenied = 19
    InboxIsFull = 20
    NoCache = 21
    NoSuchUser = 22
    NoCredentials = 23
    NetworkDisabled = 24
    InvalidDeviceId = 25
    CantOpenTraceFile = 26
    ApplicationBanned = 27
    OfflineTooManyTracks = 31
    OfflineDiskCache = 32
    OfflineExpired = 33
    OfflineNotAllowed = 34
    OfflineLicenseLost = 35
    OfflineLicenseError = 36
    LastfmAuthError = 39
    InvalidArgument = 40
    SystemFailure = 41



class SampleType:
    Int16NativeEndian = 0



class ConnectionRules:
    Network = 0x1
    NetworkIfRoaming = 0x2
    AllowSyncOverMobile = 0x4
    AllowSyncOverWifi = 0x8



class ConnectionType:
    Unknown = 0
    Disconnected = 1
    Mobile = 2
    MobileRoaming = 3
    Wifi = 4
    Wired = 5



class ConnectionState:
    LoggedOut = 0
    LoggedIn = 1
    Disconnected = 2
    Undefined = 3
    Offline = 4



class Bitrate:
    Rate160k = 0
    Rate320k = 1
    Rate96k = 2



class SocialProvider:
    Spotify = 0
    Facebook = 1
    Lastfm = 2



class ScrobblingState:
    UseGlobalSetting = 0
    LocalEnabled = 1
    LocalDisabled = 2
    GlobalEnabled = 3
    GlobalDisabled = 4



class MainLoop:
    __notify_flag = None
    __quit_flag = None
    __quit_test = None
    
    
    def __init__(self):
        self.__notify_flag = threading.Event()
        self.__quit_flag = threading.Event()
        
        #Py 2.6+
        if hasattr(self.__quit_flag, 'is_set'):
            self.__quit_test = self.__quit_flag.is_set
        
        #Fallback for earlier python versions
        else:
            self.__quit_test = self.__quit_flag.isSet
    
    
    def loop(self, session):
        timeout = None
        
        while not self.__quit_test():
            self.__notify_flag.wait(timeout)
            self.__notify_flag.clear()
            timeout = session.process_events()
    
    
    def notify(self):
        self.__notify_flag.set()
    
    
    def quit(self):
        self.__quit_flag.set()
        self.notify()



class CallbackItem:
    def __init__(self, **args):
        self.__dict__.update(args)



class CallbackQueueManager:
    _callbacks = None
    
    def __init__(self):
        self._callbacks = []
        
    def add_callback(self, condition, callback, *args):
        self._callbacks.append(
            CallbackItem(
                condition = condition,
                callback = callback,
                args = args,
            )
        )
    
    def process_callbacks(self):
        for item in self._callbacks:
            if item.condition():
                self._callbacks.remove(item)
                item.callback(*item.args)



class BulkConditionChecker:
    _conditions = None
    _event = None
    
    def __init__(self):
        self._conditions = []
        self._event = threading.Event()
    
    
    @synchronized
    def add_condition(self, condition):
        self._conditions.append(condition)
    
    
    @synchronized
    def check_conditions(self):
        #Generate a new list with false conditions
        self._conditions = [item for item in self._conditions if not item()]
            
        #If list size reaches to zero all conditions have been met
        if len(self._conditions) == 0:
            self._complete()
            return True
        
        else:
            return False
    
    
    def _complete(self):
        self._event.set()
        self.complete()
    
    
    def complete(self):
        pass
    
    
    def try_complete_wait(self, timeout = None):
        #Clear the event first, so we make a "clean" check
        self._event.clear()
        
        #Check conditions if they have been already met, and wait
        self.check_conditions()
        self._event.wait(timeout)
        
        #Return the events's status
        return self._event.isSet()
    
    
    def complete_wait(self, timeout = None):
        #Fail if the call returns due to a timeout
        if not self.try_complete_wait(timeout):
            raise RuntimeError('Timed out while waiting for an event.')



class CallbackManager:
    __callbacks = None
    
    
    def __init__(self):
        self.__callbacks = {}
    
    
    def _create_class(self, callback):
        return None
    
    
    def add_callbacks(self, callbacks):
        cb_id = id(callbacks)
        if cb_id in self.__callbacks:
            raise DuplicateCallbackError()
        else:
            self.__callbacks[cb_id] = CallbackItem(
                callbacks = callbacks,
                custom_class = self._create_class(callbacks)
            )
    
    
    def remove_callbacks(self, callbacks):
        cb_id = id(callbacks)
        if cb_id not in self.__callbacks:
            raise UnknownCallbackError()
        else:
            del self.__callbacks[cb_id]
    
    
    def remove_all_callbacks(self):
        for item in self.__callbacks.values():
            self.remove_callbacks(item.callbacks)
    
    
    def _call_funcs(self, name, *args, **kwargs):
        for item in self.__callbacks.values():
            f = getattr(item.callbacks, name)
            f(*args, **kwargs)
    
    
    def __getattr__(self, name):
        return lambda *args, **kwargs: self._call_funcs(name, *args, **kwargs)
        
    
    def __del__(self):
        self.remove_all_callbacks()
