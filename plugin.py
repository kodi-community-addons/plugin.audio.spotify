# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
import os,xbmcaddon
ADDON = xbmcaddon.Addon('plugin.audio.spotify')
libs_dir = os.path.join(ADDON.getAddonInfo('path').decode("utf-8"), "resources/lib")
sys.path.insert(0, libs_dir)
sys.path.insert(0, os.path.join(libs_dir, "libspotify"))
from utils import *
from plugincontent import Main

Main().main()