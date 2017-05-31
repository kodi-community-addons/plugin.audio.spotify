#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    Unofficial Spotify client for Kodi
'''

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "resources", "lib"))
from plugincontent import PluginContent
#main entrypoint
if __name__ == "__main__":
    PluginContent()
