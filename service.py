#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc,xbmcgui,xbmcplugin,xbmcaddon
import os.path
import sys
import urlparse


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

libs_dir = os.path.join(ADDON_PATH, "resources/lib")
sys.path.insert(0, libs_dir)
sys.path.insert(0, os.path.join(libs_dir, "libspotify"))
from utils import logMsg


#main code...
logMsg('version %s started' % ADDON_VERSION,0)
from playbackservice import main
main()
logMsg('version %s stopped' % ADDON_VERSION,0)

