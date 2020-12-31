#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    script.module.metadatautils
    channellogos.py
    Get channellogos from kodidb or logosdb
"""

import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, get_clean_image
else:
    from utils import get_json, get_clean_image
import xbmc
import xbmcvfs


class ChannelLogos(object):
    """get channellogo"""

    def __init__(self, kodidb=None):
        """Initialize - optionaly provide KodiDb object"""
        if not kodidb:
            if sys.version_info.major == 3:
                from .kodidb import KodiDb
            else:
                from kodidb import KodiDb
            self.kodidb = KodiDb()
        else:
            self.kodidb = kodidb

    def get_channellogo(self, channelname):
        """get channellogo for the supplied channelname"""
        result = {}
        for searchmethod in [self.search_kodi]:
            if result:
                break
            result = searchmethod(channelname)
        return result

    def search_kodi(self, searchphrase):
        """search kodi json api for channel logo"""
        result = ""
        if xbmc.getCondVisibility("PVR.HasTVChannels"):
            results = self.kodidb.get_json(
                'PVR.GetChannels',
                fields=["thumbnail"],
                returntype="tvchannels",
                optparam=(
                    "channelgroupid",
                    "alltv"))
            for item in results:
                if item["label"] == searchphrase:
                    channelicon = get_clean_image(item['thumbnail'])
                    if channelicon and xbmcvfs.exists(channelicon):
                        result = channelicon
                        break
        return result