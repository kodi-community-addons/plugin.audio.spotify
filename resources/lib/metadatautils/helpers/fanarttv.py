#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Get artwork for media from fanart.tv"""

import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, KODI_LANGUAGE, process_method_on_list, try_parse_int, ADDON_ID
else:
    from utils import get_json, KODI_LANGUAGE, process_method_on_list, try_parse_int, ADDON_ID
from operator import itemgetter
import xbmcaddon
import datetime


class FanartTv(object):
    """get artwork from fanart.tv"""
    base_url = 'http://webservice.fanart.tv/v3/'
    api_key = ''
    client_key = ''
    ignore_cache = False

    def __init__(self, simplecache=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        addon = xbmcaddon.Addon(ADDON_ID)
        self.client_key = addon.getSetting("fanarttv_apikey").strip()
        del addon

    def artist(self, artist_id):
        """get artist artwork"""
        data = self.get_data("music/%s" % artist_id)
        mapping_table = [("artistbackground", "fanart"), ("artistthumb", "thumb"),
                         ("hdmusiclogo", "clearlogo"), ("musiclogo", "clearlogo"), ("musicbanner", "banner")]
        return self.map_artwork(data, mapping_table)

    def album(self, album_id):
        """get album artwork"""
        artwork = {}
        data = self.get_data("music/albums/%s" % album_id)
        if data:
            mapping_table = [("cdart", "discart"), ("albumcover", "thumb")]
            if sys.version_info.major == 3:
                for item in data["albums"].values():
                    artwork.update(self.map_artwork(item, mapping_table))
            else:
                for item in data["albums"].itervalues():
                    artwork.update(self.map_artwork(item, mapping_table))
        return artwork

    def musiclabel(self, label_id):
        """get musiclabel logo"""
        artwork = {}
        data = self.get_data("music/labels/%s" % label_id)
        if data and data.get("musiclabel"):
            for item in data["musiclabel"]:
                # we just grab the first logo (as the result is sorted by likes)
                if item["colour"] == "colour" and "logo_color" not in artwork:
                    artwork["logo_color"] = item["url"]
                elif item["colour"] == "white" and "logo_white" not in artwork:
                    artwork["logo_white"] = item["url"]
        return artwork

    def movie(self, movie_id):
        """get movie artwork"""
        data = self.get_data("movies/%s" % movie_id)
        mapping_table = [("hdmovielogo", "clearlogo"), ("moviedisc", "discart"), ("movielogo", "clearlogo"),
                         ("movieposter", "poster"), ("hdmovieclearart", "clearart"), ("movieart", "clearart"),
                         ("moviebackground", "fanart"), ("moviebanner", "banner"), ("moviethumb", "landscape")]
        return self.map_artwork(data, mapping_table)

    def tvshow(self, tvshow_id):
        """get tvshow artwork"""
        data = self.get_data("tv/%s" % tvshow_id)
        mapping_table = [("hdtvlogo", "clearlogo"), ("clearlogo", "clearlogo"), ("hdclearart", "clearart"),
                         ("clearart", "clearart"), ("showbackground", "fanart"), ("tvthumb", "landscape"),
                         ("tvbanner", "banner"), ("characterart", "characterart"), ("tvposter", "poster")]
        return self.map_artwork(data, mapping_table)

    def tvseason(self, tvshow_id, season):
        """get season artwork - banner+landscape only as the seasonposters lacks a season in the json response"""
        data = self.get_data("tv/%s" % tvshow_id)
        artwork = {}
        mapping_table = [("seasonthumb", "landscape"), ("seasonbanner", "banner")]
        for artwork_mapping in mapping_table:
            fanarttv_type = artwork_mapping[0]
            kodi_type = artwork_mapping[1]
            if fanarttv_type in data:
                images = [item for item in data[fanarttv_type] if item["season"] == str(season)]
                images = process_method_on_list(self.score_image, data[fanarttv_type])
                if images:
                    images = sorted(images, key=itemgetter("score"), reverse=True)
                    images = [item["url"] for item in images]
                    artwork[kodi_type + "s"] = images
                    artwork[kodi_type] = images[0]
        return artwork

    def get_data(self, query):
        """helper method to get data from fanart.tv json API"""
        api_key = self.api_key
        if not api_key:
            api_key = '639191cb0774661597f28a47e7e2bad5'  # rate limited default api key
        url = '%s%s?api_key=%s' % (self.base_url, query, api_key)
        if self.client_key or self.api_key:
            if self.client_key:
                url += '&client_key=%s' % self.client_key
            rate_limit = None
            expiration = datetime.timedelta(days=7)
        else:
            # without personal or app provided api key = rate limiting and older info from cache
            rate_limit = ("fanart.tv", 2)
            expiration = datetime.timedelta(days=60)
        cache = self.cache.get(url)
        if cache:
            result = cache
        else:
            result = get_json(url, ratelimit=rate_limit)
            self.cache.set(url, result, expiration=expiration)
        return result

    def map_artwork(self, data, mapping_table):
        """helper method to map the artwork received from fanart.tv to kodi known formats"""
        artwork = {}
        if data:
            for artwork_mapping in mapping_table:
                fanarttv_type = artwork_mapping[0]
                kodi_type = artwork_mapping[1]
                images = []
                if fanarttv_type in data and kodi_type not in artwork:
                    # artworktype is found in the data, now do some magic to select the best one
                    images = process_method_on_list(self.score_image, data[fanarttv_type])
                # set all images in list and select the item with highest score
                if images:
                    images = sorted(images, key=itemgetter("score"), reverse=True)
                    images = [item["url"] for item in images]
                    artwork[kodi_type + "s"] = images
                    artwork[kodi_type] = images[0]
        return artwork

    @staticmethod
    def score_image(item):
        """score item based on number of likes and the language"""
        score = 0
        item["url"] = item["url"].replace(" ", "%20")
        score += try_parse_int(item["likes"])
        if "lang" in item:
            if item["lang"] == KODI_LANGUAGE:
                score += 1000
            elif item["lang"] == "en":
                score += 500
        item["score"] = score
        return item
