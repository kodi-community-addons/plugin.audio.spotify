# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
import xbmc,xbmcaddon,xbmcgui,xbmcplugin
import sys,os.path,platform,logging
import xml.etree.ElementTree as ET
from traceback import print_exc
import unicodedata
ADDON = xbmcaddon.Addon('plugin.audio.spotify')
ADDON_ID = ADDON.getAddonInfo('id').decode("utf-8")
ADDON_NAME = ADDON.getAddonInfo('name').decode("utf-8")
ADDON_PATH = ADDON.getAddonInfo('path').decode("utf-8")
ADDON_VERSION = ADDON.getAddonInfo('version').decode("utf-8")
ADDON_DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s" % ADDON_ID).decode("utf-8")
KODI_VERSION  = int(xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0])
WINDOW = xbmcgui.Window(10000)
SETTING = ADDON.getSetting
SAVESETTING = ADDON.setSetting

try: from urlparse import urlparse
except: from urllib.parse import urlparse
try: from urllib import urlencode
except: from urllib.parse import urlencode
    
try: 
    from multiprocessing.pool import ThreadPool as Pool
    supportsPool = True
except: supportsPool = False

try: import simplejson as json
except: import json

def logMsg(msg, debug=False):
    if debug: 
        loglevel = xbmc.LOGDEBUG
    else: 
        loglevel = xbmc.LOGNOTICE
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("%s --> %s" %(ADDON_NAME,msg), level=loglevel)
    if "exception" in msg.lower() and debug:
        print_exc()
     
def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method" : "%s", "params": %s, "id":1 }' %(method, params.encode("utf-8")))
    jsonobject = json.loads(json_response.decode('utf-8','replace'))
    if(jsonobject.has_key('result')):
        return jsonobject['result']
    else:
        logMsg("getJson - empty result for Method %s - params: %s - response: %s" %(method,params, str(jsonobject))) 
        return {}

def getChunks(data, chunksize):
    return[data[x:x+chunksize] for x in xrange(0, len(data), chunksize)]     

def check_dirs():
    if not os.path.exists(ADDON_DATA_PATH):
        os.makedirs(ADDON_DATA_PATH)
    sp_cache_dir = os.path.join(ADDON_DATA_PATH, 'libspotify/cache')
    sp_settings_dir = os.path.join(ADDON_DATA_PATH, 'libspotify/settings')
    if not os.path.exists(sp_cache_dir):
        os.makedirs(sp_cache_dir)
    if not os.path.exists(sp_settings_dir):
        os.makedirs(sp_settings_dir)
    return (ADDON_DATA_PATH, sp_cache_dir, sp_settings_dir)
        
class Platform:
    ANDROID = 'System.Platform.Android'
    LINUX = 'System.Platform.Linux'
    WINDOWS = 'System.Platform.Windows'
    OSX = 'System.Platform.OSX'
    IOS = 'System.Platform.IOS'
	
    @staticmethod
    def all_platforms():
        return [getattr(Platform, attr) for attr in vars(Platform) 
            if not callable(getattr(Platform, attr)) and not attr.startswith("__")]
	
class Architecture:
    X86 = "x86"
    X86_64 = "x86_64"
    ARMV6 = "armv6"
    ARMV7 = "armv7"
    AARCH64 = "aarch64"

def load_all_libraries():
    add_native_libraries()
    add_external_libraries()

def add_native_libraries():
    architecture = get_architecture()
    platform = get_platform()
    
    DLL_DIRS = {
        (Platform.LINUX, Architecture.X86) : ["resources/dlls/linux/x86"],
        (Platform.LINUX, Architecture.X86_64) : ["resources/dlls/linux/x86_64"],
        (Platform.LINUX, Architecture.ARMV6) : ["resources/dlls/linux/armv6","resources/dlls/linux/armv6hf"],
        (Platform.LINUX, Architecture.ARMV7) : ["resources/dlls/linux/armv7","resources/dlls/linux/armv6hf"],
        (Platform.LINUX, Architecture.AARCH64) : ["resources/dlls/linux/aarch64"],
        (Platform.WINDOWS, Architecture.X86) : ["resources/dlls/windows/x86"],
        (Platform.WINDOWS, Architecture.X86_64) : ["resources/dlls/windows/x86"],
        (Platform.OSX, Architecture.X86) : ["resources/dlls/osx"],		
        (Platform.OSX, Architecture.X86_64) : ["resources/dlls/osx"],
        (Platform.ANDROID, Architecture.ARMV6) : ["resources/dlls/android/arm"],
        (Platform.ANDROID, Architecture.ARMV7) : ["resources/dlls/android/arm"],
        (Platform.ANDROID, Architecture.X86) : ["resources/dlls/android/arm"],
        (Platform.ANDROID, Architecture.X86_64) : ["resources/dlls/android/arm"],
        (Platform.ANDROID, Architecture.AARCH64) : ["resources/dlls/android/arm"],
        (Platform.IOS, Architecture.ARMV6) : ["resources/dlls/ios"],
        (Platform.IOS, Architecture.ARMV7) : ["resources/dlls/ios"],
        (Platform.IOS, Architecture.X86) : ["resources/dlls/ios"]        
        }
    
    logMsg('Your platform (%s %s)' % (architecture, platform))
    dirs_to_include = DLL_DIRS.get((platform, architecture)) 
    if dirs_to_include is None or len(dirs_to_include) == 0:
        raise OSError('This platform is not supported (%s %s)' % (architecture, platform))
    add_library_paths(dirs_to_include)

def add_external_libraries():
    add_library_paths(['resources','resources/libs'])

def get_architecture():
    return get_detected_architecture()
    
def get_platform():
    return get_detected_platform()

def get_detected_architecture():
    try:
        architecture = platform.machine()
    except:
        logMsg('Could not detect architecture! Setting X86')
        logMsg(traceback.format_exc())			
        return Architecture.X86
    if architecture.startswith('armv7'):
        return Architecture.ARMV7
    elif architecture.startswith('arm'):
        return Architecture.ARMV6
    elif architecture.startswith('aarch64'):
        return Architecture.AARCH64
    elif architecture.startswith('i686') or architecture.startswith('i386'):
        return Architecture.X86
    elif architecture.startswith('AMD64') or architecture.startswith('x86_64'):
        return Architecture.X86_64

    return architecture

def get_detected_platform():
    platforms = [platform for platform in Platform.all_platforms() if xbmc.getCondVisibility(platform)]
    if len(platforms) > 0:
        return platforms.pop()
    else:
        return None

def add_library_paths(paths):
    for path in paths:
        add_library_path(path)

def add_library_path(path):
    full_path = os.path.join(ADDON_PATH, path)
    sys.path.append(full_path)

def try_encode(text, encoding="utf-8"):
    try:
        return text.encode(encoding,"ignore")
    except:
        return text       

def try_decode(text, encoding="utf-8"):
    try:
        return text.decode(encoding,"ignore")
    except:
        return text  
    
def normalize_string(text):
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
    text = text.replace("\"","")
    text = text.strip()
    text = text.rstrip('.')
    text = unicodedata.normalize('NFKD', try_decode(text))
    return text
	  
appkey = [
    0x01, 0xEF, 0x9B, 0xF4, 0xB3, 0x12, 0xBC, 0x0E, 0x84, 0x83, 0x30, 0xBB, 0x8F, 0x6A, 0xA8, 0x3A,
	0x5B, 0x6B, 0x91, 0x4E, 0x47, 0xD1, 0x4F, 0xBE, 0x4D, 0x4D, 0xE3, 0x13, 0x3D, 0x19, 0x69, 0x53,
	0x72, 0xDE, 0xA2, 0x44, 0x9B, 0x2E, 0xF6, 0xCB, 0x02, 0xD9, 0x6A, 0x77, 0xF4, 0xBE, 0xD7, 0x15,
	0x84, 0x1C, 0x5B, 0xF7, 0x07, 0xE7, 0x67, 0x9C, 0xEE, 0x27, 0x44, 0x62, 0x5C, 0xA1, 0x87, 0x4F,
	0x12, 0x38, 0xD7, 0x78, 0xDF, 0x38, 0x8F, 0xCE, 0x21, 0xE9, 0x39, 0x39, 0x91, 0x4E, 0x1E, 0x58,
	0x8D, 0xD5, 0xF3, 0xC9, 0xAB, 0xF9, 0x15, 0x4C, 0x08, 0x64, 0x8D, 0xD0, 0x34, 0x2A, 0x43, 0x41,
	0x49, 0xA4, 0x94, 0x53, 0x69, 0x23, 0xE1, 0x4E, 0xC3, 0x6F, 0x22, 0x08, 0x9B, 0x8D, 0xB4, 0x9F,
	0x30, 0x62, 0xCF, 0x06, 0x42, 0x85, 0xA4, 0x11, 0x0C, 0x7E, 0x70, 0xB2, 0xB3, 0x9D, 0xC4, 0x6E,
	0xE1, 0x6B, 0x62, 0xB4, 0xEF, 0xDB, 0x5A, 0xCA, 0x3C, 0x86, 0x0E, 0x6C, 0x59, 0x1D, 0xF4, 0x2B,
	0xFC, 0xFE, 0xF8, 0x82, 0x5A, 0x2D, 0x28, 0xC4, 0xC4, 0xA1, 0x98, 0x10, 0xF0, 0x74, 0xED, 0xC8,
	0x5D, 0x41, 0x61, 0xB3, 0x6B, 0xF2, 0x18, 0x58, 0xF9, 0x8B, 0x76, 0xEE, 0x6E, 0x43, 0x6C, 0xC8,
	0x6F, 0x38, 0x85, 0xF3, 0x5E, 0xD2, 0x7E, 0x8E, 0x4C, 0x6E, 0xA2, 0xBF, 0xC8, 0x72, 0x8E, 0xE4,
	0x11, 0x5A, 0xCA, 0xD6, 0x61, 0xEC, 0x85, 0x95, 0x20, 0x2B, 0x72, 0x31, 0xD8, 0x05, 0x0C, 0x0E,
	0xFB, 0x33, 0xA1, 0x00, 0x0C, 0x31, 0x64, 0xE7, 0x53, 0xBE, 0x9A, 0x0C, 0x3F, 0xAD, 0xDB, 0xDB,
	0x4B, 0xD3, 0xBE, 0xCD, 0x9E, 0xDD, 0x21, 0xCA, 0x46, 0xCF, 0x94, 0x19, 0xAD, 0xB5, 0x13, 0xD1,
	0x8A, 0x21, 0x44, 0x65, 0x17, 0x8C, 0xBC, 0x17, 0x26, 0x88, 0x9D, 0x7D, 0x8B, 0xF6, 0x3B, 0x90,
	0x8D, 0x91, 0x84, 0xB8, 0x2E, 0xFE, 0xF9, 0xA9, 0x95, 0x47, 0xE0, 0xDB, 0xB4, 0xC0, 0x68, 0x53,
	0xE7, 0xCC, 0x12, 0xF1, 0xA4, 0x1E, 0x33, 0x8A, 0xB9, 0xD8, 0x01, 0x17, 0x13, 0x16, 0xAB, 0x57,
	0xE5, 0xE1, 0xC0, 0x89, 0x50, 0xF6, 0x70, 0xB4, 0x79, 0x79, 0x9E, 0x0F, 0xFD, 0x71, 0xB9, 0x94,
	0x85, 0x4C, 0x66, 0xDA, 0x8D, 0x46, 0xCA, 0xF3, 0xC4, 0x64, 0xD6, 0xBB, 0x39, 0xAF, 0x47, 0xAD,
	0xC5,
]

SpotifyError = {
    0:"Ok",
    1:"Bad Api version",
    2:"Api Initialization Failed",
    3:"Track not playable",
    5:"Bad application key",
    6:"Bad username or password",
    7:"User banned",
    8:"Unable to contact server",
    9:"ClientTooOld",
    9:"OtherPermanent",
    10:"BadUserAgent",
    12:"MissingCallback",
    13:"InvalidIndata",
    14:"IndexOutOfRange",
    15:"UserNeedsPremium",
    16:"OtherTransient",
    17:"IsLoading",
    18:"NoStreamAvailable",
    19:"PermissionDenied",
    20:"InboxIsFull",
    21:"NoCache",
    22:"NoSuchUser",
    23:"NoCredentials",
    24:"NetworkDisabled",
    25:"InvalidDeviceId",
    26:"CantOpenTraceFile",
    27:"ApplicationBanned",
    31:"OfflineTooManyTracks",
    32:"OfflineDiskCache",
    33:"OfflineExpired",
    34:"OfflineNotAllowed",
    35:"OfflineLicenseLost",
    36:"OfflineLicenseError",
    39:"LastfmAuthError",
    40:"InvalidArgument",
    41:"SystemFailure",
    999:"Platform not supported for playback, continuing without playback support."
    }