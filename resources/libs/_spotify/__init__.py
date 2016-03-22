import struct, os, ctypes, sys
import weakref
from _spotify.utils import moduletracker


#Module index
__all__ = [
    "album", "albumbrowse", "artist", "artistbrowse",
    "image", "inbox", "link", "localtrack",
    "playlist", "playlistcontainer", "radio", "search",
    "session", "toplistbrowse", "track", "user", "utils",
]


#Some fallbacks for python 2.4
if hasattr(ctypes, "c_bool"):
    bool_type = ctypes.c_bool
else:
    bool_type = ctypes.c_ubyte


#Calculate void pointer size, 32 or 64
voidp_size = struct.calcsize("P") * 8

#Impor library loading routine
if os.name == "nt":
    from _ctypes import FreeLibrary as dlclose
else:
    from _ctypes import dlclose


#Platform-specific initializations
if os.name == "nt" and voidp_size == 32:
    callback = ctypes.WINFUNCTYPE

elif os.name == "posix" and voidp_size in [32,64]:
    callback = ctypes.CFUNCTYPE
    
else:
    raise OSError(
        "Cannot run in that environment (os: %s; arch: %d)" %
        (os.name, voidp_size)
    )


def is_linux():
    return sys.platform.startswith('linux')



class ModuleInterface(object):
    __registered_funcs = None
    __library = None
    
    
    def __init__(self):
        self.__registered_funcs = {}
    
    
    def _load_library(self):
        pass
    
    
    def get_library(self):
        if self.__library is None:
            self.__library = self._load_library()
        
        return self.__library
    
    
    def _get_func(self, name, restype, *argtypes):
        if name not in self.__registered_funcs:
            lib = self.get_library()
            func = getattr(lib, name)
            func.restype = restype
            func.argtypes = argtypes
            self.__registered_funcs[name] = func
        
        return self.__registered_funcs[name]



class LibSpotifyInterface(ModuleInterface):
    def __init__(self):
        ModuleInterface.__init__(self)
        moduletracker.track_module(self)
    
    
    def _load_library(self):
        ll = CachingLibraryLoader()
        return ll.load('libspotify')



_library_cache = {}



def unload_library(name):
    if os.name != 'nt':
        """
        Don't unload the library on windows, as it may result in a crash when
        this gets really unloaded.
        """
        if name in _library_cache:
            dlclose(_library_cache[name]._handle)
            del _library_cache[name]



def can_unload_library():
    return moduletracker.count_tracked_modules() == 0



def _get_handle_by_name(name):
    if os.name != 'nt':
        raise RuntimeError('This function is Windows only.')
    
    #Get a reference to GetModuleHandle
    k32 = ctypes.windll.kernel32
    get_handle = k32.GetModuleHandleA
    get_handle.argtypes = [ctypes.c_char_p]
    get_handle.restype = ctypes.c_ulong
    
    return get_handle(name)



class CachingLibraryLoader:
    def _get_filename(self, name):
        if os.name == 'nt':
            return '%s.dll' % name
        
        elif os.name == 'posix':
            if sys.platform == 'darwin':
                return name
            
            else:
                return '%s.so' % name
    
    
    def _get_loader(self):
        if os.name == 'nt':
            return ctypes.windll
        
        elif os.name == 'posix':
            return ctypes.cdll
    
    
    def _load_from_sys_path(self, loader, name):
        filename = self._get_filename(name)
        for path in sys.path:
            full_path = os.path.join(path, filename)
            
            #Library file exists
            if os.path.isfile(full_path):
                try:
                    return loader.LoadLibrary(full_path)
                
                #An exception may indicate wrong arch or abi, continue loop
                except:
                    pass
    
        raise OSError("Unable to find '%s'" % name)
    
    
    def _load(self, name):
        loader = self._get_loader()
        
        #Unload on Windows first
        if os.name == 'nt':
            handle = _get_handle_by_name(name)
            if handle != 0:
                dlclose(handle)
        
        #Let ctypes find it
        try:
            return getattr(loader, name)
    
        #Bad luck, let's search on sys.path
        except OSError:
            return self._load_from_sys_path(loader, name)
    
    
    def load(self, name):
        #Load if not found on the cache 
        if name not in _library_cache:
            _library_cache[name] = self._load(name)
        
        return _library_cache[name]



#structure definitions
class audioformat(ctypes.Structure):
    pass

class subscribers(ctypes.Structure):
    pass

class audio_buffer_stats(ctypes.Structure):
    pass



#completion of types
audioformat._fields_ = [
    ("sample_type", ctypes.c_int),
    ("sample_rate", ctypes.c_int),
    ("channels", ctypes.c_int),
]

subscribers._fields_ = [
    ("count", ctypes.c_uint),
    ("subscribers", ctypes.c_char_p * 1),
]

audio_buffer_stats._fields_ = [
    ("samples", ctypes.c_int),
    ("stutter", ctypes.c_int),
]



#Low level declaration interface
class SpotifyInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)
    
    
    def error_message(self, *args):
        return self._get_func(
            'sp_error_message',
            ctypes.c_char_p,
            ctypes.c_int
        )(*args)
    
    
    def build_id(self, *args):
        return self._get_func(
            'build_id',
            'sp_build_id',
            ctypes.c_char_p
        )(*args)
