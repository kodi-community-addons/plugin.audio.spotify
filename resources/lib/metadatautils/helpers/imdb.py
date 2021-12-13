#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    script.module.metadatautils
    imdb.py
    Get metadata from imdb
"""

import os, sys
if sys.version_info.major == 3:
    from .utils import requests, try_parse_int
else:
    from utils import requests, try_parse_int
import bs4 as BeautifulSoup
from simplecache import use_cache


class Imdb(object):
    """Info from IMDB (currently only top250)"""

    def __init__(self, simplecache=None, kodidb=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        if not kodidb:
            if sys.version_info.major == 3:
                from .kodidb import KodiDb
            else:
                from kodidb import KodiDb
            self.kodidb = KodiDb()
        else:
            self.kodidb = kodidb

    @use_cache(2)
    def get_top250_rating(self, imdb_id):
        """get the top250 rating for the given imdbid"""
        return {"IMDB.Top250": self.get_top250_db().get(imdb_id, 0)}

    @use_cache(7)
    def get_top250_db(self):
        """
            get the top250 listing for both movies and tvshows as dict with imdbid as key
            uses 7 day cache to prevent overloading the server
        """
        results = {}
        for listing in [("top", "chttp_tt_"), ("toptv", "chttvtp_tt_")]:
            html = requests.get(
                "http://www.imdb.com/chart/%s" %
                listing[0], headers={
                    'User-agent': 'Mozilla/5.0'}, timeout=20)
            soup = BeautifulSoup.BeautifulSoup(html.text, features="html.parser")
            for table in soup.findAll('table'):
                if not table.get("class") == "chart full-width":
                    for td_def in table.findAll('td'):
                        if not td_def.get("class") == "titleColumn":
                            a_link = td_def.find("a")
                            if a_link:
                                url = a_link["href"]
                                imdb_id = url.split("/")[2]
                                imdb_rank = url.split(listing[1])[1]
                                results[imdb_id] = try_parse_int(imdb_rank)
        self.write_kodidb(results)
        return results

    def write_kodidb(self, results):
        """store the top250 position in kodi database to access it with ListItem.Top250"""
        for imdb_id in results:
            kodi_movie = self.kodidb.movie_by_imdbid(imdb_id)
            if kodi_movie:
                params = {
                    "movieid": kodi_movie["movieid"],
                    "top250": results[imdb_id]
                }
                self.kodidb.set_json('VideoLibrary.SetMovieDetails', params)
