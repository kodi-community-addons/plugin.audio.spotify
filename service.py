#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    Main service entry point
'''
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "resources", "lib"))

from main_service import MainService
MainService()
