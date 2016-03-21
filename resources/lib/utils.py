# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
import xbmc,xbmcaddon,xbmcgui,xbmcplugin
import sys,os.path,platform,logging
import xml.etree.ElementTree as ET
from traceback import print_exc
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

def logMsg(msg, level = 1):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    if "exception" in msg.lower() or "error" in msg.lower():
        xbmc.log("%s --> %s" %(ADDON_NAME,msg), level=xbmc.LOGERROR)
        print_exc()
    else: 
        xbmc.log("%s --> %s" %(ADDON_NAME,msg), level=xbmc.LOGNOTICE)
     
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
 
def get_architecture():
    try:
        machine = platform.machine()

        #Some filtering...
        if machine.startswith('armv6'):
            return 'armv6'

        elif machine.startswith('i686'):
            return 'x86'

    except:
        return None

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
        
def add_dll_path(path):
    #Build the full path and publish it
    full_path = os.path.join(ADDON_PATH, path)
    sys.path.append(full_path)


def set_dll_paths(base_dir):
    arch_str = get_architecture()

    if xbmc.getCondVisibility('System.Platform.Linux'):
        if arch_str in(None, 'x86'):
            add_dll_path(os.path.join(base_dir, 'linux/x86'))

        if arch_str in(None, 'x86_64'):
            add_dll_path(os.path.join(base_dir, 'linux/x86_64'))

        if arch_str in(None, 'armv6'):
            add_dll_path(os.path.join(base_dir, 'linux/armv6hf'))
            add_dll_path(os.path.join(base_dir, 'linux/armv6'))

    elif xbmc.getCondVisibility('System.Platform.Windows'):
        if arch_str in(None, 'x86'):
            add_dll_path(os.path.join(base_dir, 'windows/x86'))
        else:
            raise OSError('Sorry, only 32bit Windows is supported.')

    elif xbmc.getCondVisibility('System.Platform.OSX'):
        add_dll_path(os.path.join(base_dir, 'osx'))

    elif xbmc.getCondVisibility('System.Platform.Android'):
        add_dll_path(os.path.join(base_dir, 'android'))

    else:
        raise OSError('Sorry, this platform is not supported.')

_trans_table = {
    logging.DEBUG: xbmc.LOGDEBUG,
    logging.INFO: xbmc.LOGINFO,
    logging.WARNING: xbmc.LOGWARNING,
    logging.ERROR: xbmc.LOGERROR,
    logging.CRITICAL: xbmc.LOGSEVERE,
}


class XbmcHandler(logging.Handler):
    def emit(self, record):
        xbmc_level = _trans_table[record.levelno]
        xbmc.log(record.msg, xbmc_level)

def setup_logging():
    handler = XbmcHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

def get_logger():
    return logging.getLogger('Spotify')
        
appkey = [
    0x01, 0xBD, 0x09, 0xB2, 0x73, 0xD4, 0x86, 0x11, 0x01, 0x5A, 0xAA, 0x6C, 0xA4, 0xFA, 0x93, 0x48,
    0x3D, 0x9B, 0x67, 0xEB, 0xA8, 0x44, 0x1C, 0x1F, 0x28, 0xD5, 0x0B, 0x22, 0x29, 0xD7, 0x5A, 0xE2,
    0x79, 0x39, 0x4A, 0x11, 0x98, 0xF3, 0x4B, 0xE6, 0x50, 0xED, 0x37, 0x28, 0xBB, 0x8B, 0x46, 0xB7,
    0x7E, 0xE5, 0xBD, 0xC8, 0xA2, 0x1A, 0xB5, 0xC1, 0x80, 0x97, 0x13, 0x5B, 0x52, 0xE2, 0xB2, 0x7C,
    0x83, 0x22, 0x30, 0x8A, 0x1A, 0xE8, 0xA4, 0xD5, 0x57, 0x46, 0xEF, 0xB2, 0x39, 0x60, 0x89, 0xFB,
    0x68, 0x8A, 0x0B, 0x52, 0x64, 0xB6, 0x50, 0xA9, 0x8A, 0xE5, 0x7C, 0x12, 0x49, 0x61, 0x53, 0x73,
    0x40, 0x6C, 0xF0, 0x6B, 0xDA, 0x1B, 0x99, 0x83, 0x4A, 0xBB, 0x19, 0x86, 0xF2, 0x25, 0xB1, 0xA6,
    0x45, 0x2B, 0x4E, 0xC9, 0xF6, 0x9E, 0x4D, 0x8E, 0x2E, 0x42, 0x5F, 0x1F, 0xAF, 0xC8, 0x4A, 0xA3,
    0xEB, 0xA8, 0x12, 0x5D, 0x5F, 0xBF, 0x3D, 0x37, 0xE3, 0xD4, 0xF2, 0xB5, 0xAD, 0x57, 0xD7, 0xC4,
    0x96, 0xF5, 0x94, 0x4F, 0x80, 0xD6, 0xCE, 0x30, 0x3D, 0x40, 0x54, 0x30, 0x9F, 0xED, 0xB3, 0xB4,
    0xAA, 0x35, 0xDD, 0x76, 0x4A, 0xB6, 0xEB, 0x4C, 0x9D, 0x46, 0x7F, 0xFC, 0xF4, 0x7A, 0xE6, 0x7E,
    0xEC, 0x76, 0x07, 0x99, 0xE5, 0x7B, 0x4A, 0xE1, 0x69, 0xFB, 0xCA, 0xEA, 0x19, 0x2B, 0x6D, 0x0D,
    0x4A, 0xD2, 0x5B, 0x49, 0x3E, 0x5A, 0xCC, 0xA4, 0xF4, 0xD2, 0xAF, 0xE7, 0x43, 0xBB, 0xE9, 0xEA,
    0xA3, 0x0F, 0x00, 0xC2, 0x78, 0xCC, 0x7C, 0xC3, 0x44, 0xDC, 0x9A, 0x1B, 0x49, 0x75, 0xE9, 0x37,
    0xA6, 0x61, 0x06, 0x43, 0xDF, 0x65, 0xD0, 0xCF, 0x67, 0xCC, 0x01, 0x76, 0x7B, 0x2D, 0x55, 0x79,
    0x57, 0x5C, 0x9B, 0xBE, 0x5A, 0x8D, 0xAB, 0xD3, 0xF6, 0x00, 0xE8, 0xA5, 0x79, 0xDD, 0xA2, 0xF5,
    0xBB, 0xA1, 0xD1, 0x3F, 0x66, 0xFE, 0x3C, 0x2A, 0x69, 0xE7, 0x34, 0x6A, 0xC1, 0x18, 0xB5, 0xD6,
    0xAC, 0x82, 0xAE, 0xD5, 0xAF, 0xA8, 0x9B, 0x66, 0x26, 0x74, 0x8A, 0xAB, 0x11, 0xA4, 0x8B, 0xF0,
    0xC5, 0x02, 0xDB, 0x47, 0xFC, 0x89, 0x03, 0x55, 0xCB, 0x1E, 0xD1, 0x45, 0xC5, 0xBB, 0x99, 0xEE,
    0xBC, 0xAB, 0x20, 0x6F, 0x30, 0xA3, 0x31, 0x07, 0x00, 0x58, 0x2B, 0x38, 0xE1, 0xE8, 0x99, 0xCD,
    0x03,
]