'''
Copyright 2011 Mikel Azkolain

This file is part of Spotify.

Spotify is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotify is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotify.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc,xbmcaddon,xbmcgui
from __main__ import ADDON_VERSION, ADDON_PATH,SETTING,ADDON_NAME,ADDON_ID
import sys,os.path,platform
import xml.etree.ElementTree as ET
from traceback import print_exc


def logMsg(msg, level = 1):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    if "exception" in msg.lower() or "error" in msg.lower():
        xbmc.log("%s --> %s" %(ADDON_NAME,msg), level=xbmc.LOGERROR)
        print_exc()
    else: 
        xbmc.log("%s --> %s" %(ADDON_NAME,msg), level=xbmc.LOGNOTICE)

class CacheManagement:
    Automatic = 0
    Manual = 1


class StreamQuality:
    Low = 0
    Medium = 1
    High = 2


class StartupScreen:
    NewStuff = 0
    Playlists = 1


class SettingsManager:
    __addon = None

    def __init__(self):
        self.__addon = xbmcaddon.Addon(id=ADDON_ID)

    def _get_setting(self, name):
        return self.__addon.getSetting(name)

    def _set_setting(self, name, value):
        return self.__addon.setSetting(name, value)

    def get_addon_obj(self):
        return self.__addon

    def get_legal_warning_shown(self):
        return self._get_setting('_legal_warning_shown') == 'true'

    def set_legal_warning_shown(self, status):
        if status:
            str_status = 'true'
        else:
            str_status = 'false'

        return self._set_setting('_legal_warning_shown', str_status)

    def get_last_run_version(self):
        return self._get_setting('_last_run_version')

    def set_last_run_version(self, version):
        return self._set_setting('_last_run_version', version)

    def get_cache_status(self):
        return self._get_setting('general_cache_enable') == 'true'

    def get_cache_management(self):
        return int(self._get_setting('general_cache_management'))

    def get_cache_size(self):
        return int(float(self._get_setting('general_cache_size')))

    def get_audio_hide_unplayable(self):
        return self._get_setting('audio_hide_unplayable') == 'true'

    def get_audio_normalize(self):
        return self._get_setting('audio_normalize') == 'true'

    def get_audio_quality(self):
        return int(self._get_setting('audio_quality'))

    def get_misc_startup_screen(self):
        return int(self._get_setting('misc_startup_screen'))

    def show_dialog(self):
        #Show the dialog
        self.__addon.openSettings()


class GuiSettingsReader:
    __guisettings_doc = None

    def __init__(self):
        settings_path = xbmc.translatePath('special://profile/guisettings.xml')
        self.__guisettings_doc = ET.parse(settings_path)

    def get_setting(self, query):
        #Check if the argument is valid
        if query == '':
            raise KeyError()

        #Get the steps to the node
        step_list = query.split('.')
        root_tag = step_list[0]

        if len(step_list) > 1:
            path_remainder = '/'.join(step_list[1:])
        else:
            path_remainder = ''

        #Fail if the first tag does not match with the root
        if self.__guisettings_doc.getroot().tag != root_tag:
            raise KeyError()

        #Fail also if the element is not found
        el = self.__guisettings_doc.find(path_remainder)
        if el is None:
            raise KeyError()

        return el.text

def set_library_paths():
    #Set local library paths
    libs_dir = os.path.join(__addon_path__, "resources/lib")
    sys.path.insert(0, libs_dir)
    sys.path.insert(0, os.path.join(libs_dir, "xbmc-skinutils/src"))
    sys.path.insert(0, os.path.join(libs_dir, "cherrypy"))
    sys.path.insert(0, os.path.join(libs_dir, "taskutils/src"))
    sys.path.insert(0, os.path.join(libs_dir, "pyspotify-ctypes/src"))
    sys.path.insert(0, os.path.join(libs_dir, "pyspotify-ctypes-proxy/src"))


def has_background_support():
    return True


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