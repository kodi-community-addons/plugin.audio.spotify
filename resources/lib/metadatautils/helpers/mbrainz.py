#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    script.module.metadatautils
    mbrainz.py
    Get metadata from musicbrainz
"""

import os, sys
if sys.version_info.major == 3:
    from .utils import ADDON_ID, get_compare_string, log_msg
else:
    from utils import ADDON_ID, get_compare_string, log_msg
from simplecache import use_cache
import xbmcvfs
import xbmcaddon
import xbmc


class MusicBrainz(object):
    """get metadata from musicbrainz"""
    ignore_cache = False

    def __init__(self, simplecache=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        import musicbrainzngs as mbrainz
        mbrainz.set_useragent(
            "script.skin.helper.service",
            "1.0.0",
            "https://github.com/marcelveldt/script.skin.helper.service")
        mbrainz.set_rate_limit(limit_or_interval=2.0, new_requests=1)
        addon = xbmcaddon.Addon(ADDON_ID)
        if addon.getSetting("music_art_mb_mirror"):
            mbrainz.set_hostname(addon.getSetting("music_art_mb_mirror"))
        del addon
        self.mbrainz = mbrainz

    @use_cache(60)
    def search(self, artist, album, track):
        """get musicbrainz id by query of artist, album and/or track"""
        albumid = ""
        artistid = ""
        try:

            # lookup with artist and album (preferred method)
            if artist and album:
                artistid, albumid = self.search_release_group_match(artist, album)

            # lookup with artist and track (if no album provided)
            if not (artistid and albumid) and artist and track:
                artistid, albumid = self.search_recording_match(artist, track)

            # last resort: lookup with trackname as album
            if not (artistid and albumid) and artist and track:
                artistid, albumid = self.search_release_group_match(artist, track)

        except Exception as exc:
            log_msg("Error in musicbrainz.search: %s" % str(exc), xbmc.LOGWARNING)

        return artistid, albumid

    def get_artist_id(self, artist, album, track):
        """get musicbrainz id by query of artist, album and/or track"""
        return self.search(artist, album, track)[0]

    def get_album_id(self, artist, album, track):
        """get musicbrainz id by query of artist, album and/or track"""
        return self.search(artist, album, track)[1]

    @use_cache(60)
    def get_albuminfo(self, mbalbumid):
        """get album info from musicbrainz"""
        result = {}
        try:
            data = self.mbrainz.get_release_group_by_id(mbalbumid, includes=["tags", "ratings"])
            if data and data.get("release-group"):
                data = data["release-group"]
                result["year"] = data.get("first-release-date", "").split("-")[0]
                result["title"] = data.get("title", "")
                if data.get("rating") and data["rating"].get("rating"):
                    result["rating"] = data["rating"].get("rating")
                    result["votes"] = data["rating"].get("votes", 0)
                if data.get("tag-list"):
                    result["tags"] = []
                    result["genre"] = []
                    for tag in data["tag-list"]:
                        if tag["count"] and int(tag["count"]) > 1:
                            if " / " in tag["name"]:
                                taglst = tag["name"].split(" / ")
                            elif "/" in tag["name"]:
                                taglst = tag["name"].split("/")
                            elif " - " in tag["name"]:
                                taglst = tag["name"].split(" - ")
                            elif "-" in tag["name"]:
                                taglst = tag["name"].split("-")
                            else:
                                taglst = [tag["name"]]
                            for item in taglst:
                                if item not in result["tags"]:
                                    result["tags"].append(item)
                                if item not in result["genre"] and int(tag["count"]) > 4:
                                    result["genre"].append(item)
        except Exception as exc:
            log_msg("Error in musicbrainz - get album details: %s" % str(exc), xbmc.LOGWARNING)
        return result

    @staticmethod
    def get_albumthumb(albumid):
        """get album thumb"""
        thumb = ""
        url = "http://coverartarchive.org/release-group/%s/front" % albumid
        if xbmcvfs.exists(url):
            thumb = url
        return thumb

    @use_cache(14)
    def search_release_group_match(self, artist, album):
        """try to get a match on releasegroup for given artist/album combi"""
        artistid = ""
        albumid = ""
        mb_albums = self.mbrainz.search_release_groups(query=album,
                                                       limit=20, offset=None, strict=False, artist=artist)

        if mb_albums and mb_albums.get("release-group-list"):
            for albumtype in ["Album", "Single", ""]:
                if artistid and albumid:
                    break
                for mb_album in mb_albums["release-group-list"]:
                    if artistid and albumid:
                        break
                    if mb_album and isinstance(mb_album, dict):
                        if albumtype and albumtype != mb_album.get("primary-type", ""):
                            continue
                        if mb_album.get("artist-credit"):
                            artistid = self.match_artistcredit(mb_album["artist-credit"], artist)
                        if artistid:
                            albumid = mb_album.get("id", "")
                            break
        return artistid, albumid

    @staticmethod
    def match_artistcredit(artist_credit, artist):
        """find match for artist in artist-credits"""
        artistid = ""
        for mb_artist in artist_credit:
            if artistid:
                break
            if isinstance(mb_artist, dict) and mb_artist.get("artist", ""):
                # safety check - only allow exact artist match
                foundartist = mb_artist["artist"].get("name")
                if sys.version_info.major < 3:
                    foundartist = foundartist.encode("utf-8").decode("utf-8")
                if foundartist and get_compare_string(foundartist) == get_compare_string(artist):
                    artistid = mb_artist.get("artist").get("id")
                    break
                if not artistid and mb_artist["artist"].get("alias-list"):
                    alias_list = [get_compare_string(item["alias"])
                                  for item in mb_artist["artist"]["alias-list"]]
                    if get_compare_string(artist) in alias_list:
                        artistid = mb_artist.get("artist").get("id")
                        break
                    for item in artist.split("&"):
                        item = get_compare_string(item)
                        if item in alias_list or item in get_compare_string(foundartist):
                            artistid = mb_artist.get("artist").get("id")
                            break
        return artistid

    @use_cache(14)
    def search_recording_match(self, artist, track):
        """
            try to get the releasegroup (album) for the given artist/track combi
            various-artists compilations are ignored
        """
        artistid = ""
        albumid = ""
        mb_albums = self.mbrainz.search_recordings(query=track,
                                                   limit=20, offset=None, strict=False, artist=artist)
        if mb_albums and mb_albums.get("recording-list"):
            for mb_recording in mb_albums["recording-list"]:
                if albumid and artistid:
                    break
                if mb_recording and isinstance(mb_recording, dict):
                    # look for match on artist
                    if mb_recording.get("artist-credit"):
                        artistid = self.match_artistcredit(mb_recording["artist-credit"], artist)
                    # if we have a match on artist, look for match in release list
                    if artistid:
                        if mb_recording.get("release-list"):
                            for mb_release in mb_recording["release-list"]:
                                if mb_release.get("artist-credit"):
                                    if mb_release["artist-credit"][0].get("id", "") == artistid:
                                        albumid = mb_release["release-group"]["id"]
                                        break
                                    else:
                                        continue
                                if mb_release.get("artist-credit-phrase", "") == 'Various Artists':
                                    continue
                                # grab release group details to make sure we're
                                # not looking at some various artists compilation
                                mb_album = self.mbrainz.get_release_group_by_id(
                                    mb_release["release-group"]["id"], includes=["artist-credits"])
                                mb_album = mb_album["release-group"]
                                if mb_album.get("artist-credit"):
                                    artistid = self.match_artistcredit(mb_album["artist-credit"], artist)
                                    if artistid:
                                        albumid = mb_release["release-group"]["id"]
                                        break
        return artistid, albumid
