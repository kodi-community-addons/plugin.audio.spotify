#!/usr/bin/python
# -*- coding: utf-8 -*-

"""get metadata from the lastfm"""

import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, strip_newlines, get_compare_string
else:
    from utils import get_json, strip_newlines, get_compare_string
from simplecache import use_cache
import xbmcvfs


class LastFM(object):
    """get metadata from the lastfm"""
    api_key = "1869cecbff11c2715934b45b721e6fb0"
    ignore_cache = False

    def __init__(self, simplecache=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache

    def search(self, artist, album, track):
        """get musicbrainz id's by query of artist, album and/or track"""
        artistid = ""
        albumid = ""
        artist = artist.lower()
        if artist and album:
            params = {'method': 'album.getInfo', 'artist': artist, 'album': album}
            data = self.get_data(params)
            if data and data.get("album"):
                lfmdetails = data["album"]
                if lfmdetails.get("mbid"):
                    albumid = lfmdetails.get("mbid")
                if lfmdetails.get("tracks") and lfmdetails["tracks"].get("track"):
                    for track in lfmdetails.get("tracks")["track"]:
                        found_artist = get_compare_string(track["artist"]["name"])
                        if found_artist == get_compare_string(artist) and track["artist"].get("mbid"):
                            artistid = track["artist"]["mbid"]
                            break
        if not (artistid or albumid) and artist and track:
            params = {'method': 'track.getInfo', 'artist': artist, 'track': track}
            data = self.get_data(params)
            if data and data.get("track"):
                lfmdetails = data["track"]
                if lfmdetails.get('album position="1"'):
                    albumid = lfmdetails['album position="1"'].get("mbid")
                if lfmdetails.get("artist") and lfmdetails["artist"].get("name"):
                    found_artist = get_compare_string(lfmdetails["artist"]["name"])
                    if found_artist == get_compare_string(artist) and lfmdetails["artist"].get("mbid"):
                        artistid = lfmdetails["artist"]["mbid"]
        return artistid, albumid

    def get_artist_id(self, artist, album, track):
        """get musicbrainz id by query of artist, album and/or track"""
        return self.search(artist, album, track)[0]

    def get_album_id(self, artist, album, track):
        """get musicbrainz id by query of artist, album and/or track"""
        return self.search(artist, album, track)[1]

    def artist_info(self, artist_id):
        """get artist metadata by musicbrainz id"""
        details = {"art": {}}
        params = {'method': 'artist.getInfo', 'mbid': artist_id}
        data = self.get_data(params)
        if data and data.get("artist"):
            lfmdetails = data["artist"]
            #if lfmdetails.get("image"):
            #    for image in lfmdetails["image"]:
            #        if image["size"] in ["mega", "extralarge"] and xbmcvfs.exists(image["#text"]):
            #            details["art"]["thumbs"] = [image["#text"]]
            #            details["art"]["thumb"] = image["#text"]
            if lfmdetails.get("bio") and lfmdetails["bio"].get("content"):
                details["plot"] = strip_newlines(lfmdetails["bio"]["content"].split(' <a href')[0])
            if lfmdetails.get("stats") and lfmdetails["stats"].get("listeners"):
                details["lastfm.listeners"] = lfmdetails["stats"]["listeners"]
            if lfmdetails.get("stats") and lfmdetails["stats"].get("playcount"):
                details["lastfm.playcount"] = lfmdetails["stats"]["playcount"]
            if lfmdetails.get("tags") and lfmdetails["tags"].get("tag"):
                details["lastfm.tags"] = [tag["name"] for tag in lfmdetails["tags"]["tag"]]
            if lfmdetails.get("similar") and lfmdetails["similar"].get("artist"):
                similar_artists = []
                for count, item in enumerate(lfmdetails["similar"]["artist"]):
                    similar_artists.append(item["name"])
                    details["lastfm.similarartists.%s.name" % count] = item["name"]
                    #if item.get("image"):
                    #    for image in item["image"]:
                    #        if image["size"] in ["mega", "extralarge", "large"] and xbmcvfs.exists(image["#text"]):
                    #            details["lastfm.similarartists.%s.thumb" % count] = image["#text"]
                    #            break
                details["lastfm.similarartists"] = similar_artists

        return details

    def album_info(self, album_id):
        """get album metadata by musicbrainz id"""
        details = {"art": {}}
        params = {'method': 'album.getInfo', 'mbid': album_id}
        data = self.get_data(params)
        if data and data.get("album"):
            if isinstance(data["album"], list):
                lfmdetails = data["album"][0]
            else:
                lfmdetails = data["album"]
            #if lfmdetails.get("image"):
            #    for image in lfmdetails["image"]:
            #        if image["size"] in ["mega", "extralarge"] and xbmcvfs.exists(image["#text"]):
            #            details["art"]["thumbs"] = [image["#text"]]
            #            details["art"]["thumb"] = image["#text"]
            if lfmdetails.get("listeners"):
                details["lastfm.listeners"] = lfmdetails["listeners"]
            if lfmdetails.get("playcount"):
                details["lastfm.playcount"] = lfmdetails["playcount"]
            if lfmdetails.get("tags") and lfmdetails["tags"].get("tag"):
                details["lastfm.tags"] = [tag["name"] for tag in lfmdetails["tags"]["tag"]]
            if lfmdetails.get("wiki"):
                details["plot"] = strip_newlines(lfmdetails["wiki"].get("content", "").split(' <a')[0])

    @use_cache(30)
    def get_data(self, params):
        """helper method to get data from lastfm json API"""
        params["format"] = "json"
        params["api_key"] = self.api_key
        data = get_json('http://ws.audioscrobbler.com/2.0/', params)
        if data:
            return data
        else:
            return {}
