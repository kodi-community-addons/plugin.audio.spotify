# -*- coding: utf8 -*-
from resources.utils import logMsg, WINDOW
import resources.playbackservice as service

#execute main code
if not WINDOW.getProperty("SpotifyServiceRunning"):
    WINDOW.setProperty("SpotifyServiceRunning","running")
    logMsg("Starting background service...")
    service.main()
    logMsg("Background service stopped")
    WINDOW.clearProperty("SpotifyServiceRunning")
else:
    logMsg("Service already running")
