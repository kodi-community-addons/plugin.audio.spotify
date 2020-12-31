#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    script.module.metadatautils
    tmdb.py
    Get metadata from The Movie Database
"""

import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, KODI_LANGUAGE, try_parse_int, DialogSelect, get_compare_string, int_with_commas, ADDON_ID
else:
    from utils import get_json, KODI_LANGUAGE, try_parse_int, DialogSelect, get_compare_string, int_with_commas, ADDON_ID
from difflib import SequenceMatcher as SM
from simplecache import use_cache
from operator import itemgetter
import xbmc
import xbmcgui
import xbmcaddon
import datetime


class Tmdb(object):
    """get metadata from tmdb"""
    api_key = None  # public var to be set by the calling addon

    def __init__(self, simplecache=None, api_key=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        addon = xbmcaddon.Addon(id=ADDON_ID)
        # personal api key (preferred over provided api key)
        api_key = addon.getSetting("tmdb_apikey")
        if api_key:
            self.api_key = api_key
        del addon

    def search_movie(self, title, year="", manual_select=False, ignore_cache=False):
        """
            Search tmdb for a specific movie, returns full details of best match
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
            manual_select: (optional) if True will show select dialog with all results
        """
        details = self.select_best_match(self.search_movies(title, year), manual_select=manual_select)
        if details:
            details = self.get_movie_details(details["id"])
        return details

    @use_cache(30)
    def search_movieset(self, title):
        """search for movieset details providing the title of the set"""
        details = {}
        params = {"query": title, "language": KODI_LANGUAGE}
        result = self.get_data("search/collection", params)
        if result:
            set_id = result[0]["id"]
            details = self.get_movieset_details(set_id)
        return details

    @use_cache(4)
    def search_tvshow(self, title, year="", manual_select=False, ignore_cache=False):
        """
            Search tmdb for a specific movie, returns full details of best match
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
            manual_select: (optional) if True will show select dialog with all results
        """
        details = self.select_best_match(self.search_tvshows(title, year), manual_select=manual_select)
        if details:
            details = self.get_tvshow_details(details["id"])
        return details

    @use_cache(4)
    def search_video(self, title, prefyear="", preftype="", manual_select=False, ignore_cache=False):
        """
            Search tmdb for a specific entry (can be movie or tvshow), returns full details of best match
            parameters:
            title: (required) the title of the movie/tvshow to search for
            prefyear: (optional) prefer result if year matches
            preftype: (optional) prefer result if type matches
            manual_select: (optional) if True will show select dialog with all results
        """
        results = self.search_videos(title)
        details = self.select_best_match(results, prefyear=prefyear, preftype=preftype,
                                         preftitle=title, manual_select=manual_select)
        if details and details["media_type"] == "movie":
            details = self.get_movie_details(details["id"])
        elif details and "tv" in details["media_type"]:
            details = self.get_tvshow_details(details["id"])
        return details

    @use_cache(4)
    def search_videos(self, title):
        """
            Search tmdb for a specific entry (can be movie or tvshow), parameters:
            title: (required) the title of the movie/tvshow to search for
        """
        results = []
        page = 1
        maxpages = 5
        while page < maxpages:
            params = {"query": title, "language": KODI_LANGUAGE, "page": page}
            subresults = self.get_data("search/multi", params)
            page += 1
            if subresults:
                for item in subresults:
                    if item["media_type"] in ["movie", "tv"]:
                        results.append(item)
            else:
                break
        return results

    @use_cache(4)
    def search_movies(self, title, year=""):
        """
            Search tmdb for a specific movie, returns a list of all closest matches
            parameters:
            title: (required) the title of the movie to search for
            year: (optional) the year of the movie to search for (enhances search result if supplied)
        """
        params = {"query": title, "language": KODI_LANGUAGE}
        if year:
            params["year"] = try_parse_int(year)
        return self.get_data("search/movie", params)

    @use_cache(4)
    def search_tvshows(self, title, year=""):
        """
            Search tmdb for a specific tvshow, returns a list of all closest matches
            parameters:
            title: (required) the title of the tvshow to search for
            year: (optional) the first air date year of the tvshow to search for (enhances search result if supplied)
        """
        params = {"query": title, "language": KODI_LANGUAGE}
        if year:
            params["first_air_date_year"] = try_parse_int(year)
        return self.get_data("search/tv", params)

    def get_actor(self, name):
        """
            Search tmdb for a specific actor/person, returns the best match as kodi compatible dict
            required parameter: name --> the name of the person
        """
        params = {"query": name, "language": KODI_LANGUAGE}
        result = self.get_data("search/person", params)
        if result:
            result = result[0]
            cast_thumb = "https://image.tmdb.org/t/p/original%s" % result[
                "profile_path"] if result["profile_path"] else ""
            item = {"name": result["name"],
                    "thumb": cast_thumb,
                    "roles": [item["title"] if item.get("title") else item["name"] for item in result["known_for"]]}
            return item
        else:
            return {}

    def get_movie_details(self, movie_id):
        """get all moviedetails"""
        params = {
            "append_to_response": "keywords,videos,credits,images",
            "include_image_language": "%s,en" % KODI_LANGUAGE,
            "language": KODI_LANGUAGE
        }
        return self.map_details(self.get_data("movie/%s" % movie_id, params), "movie")

    def get_movieset_details(self, movieset_id):
        """get all moviesetdetails"""
        details = {"art": {}}
        params = {"language": KODI_LANGUAGE}
        result = self.get_data("collection/%s" % movieset_id, params)
        if result:
            details["title"] = result["name"]
            details["plot"] = result["overview"]
            details["tmdb_id"] = result["id"]
            details["art"]["poster"] = "https://image.tmdb.org/t/p/original%s" % result["poster_path"]
            details["art"]["fanart"] = "https://image.tmdb.org/t/p/original%s" % result["backdrop_path"]
            details["totalmovies"] = len(result["parts"])
        return details

    def get_tvshow_details(self, tvshow_id):
        """get all tvshowdetails"""
        params = {
            "append_to_response": "keywords,videos,external_ids,credits,images",
            "include_image_language": "%s,en" % KODI_LANGUAGE,
            "language": KODI_LANGUAGE
        }
        return self.map_details(self.get_data("tv/%s" % tvshow_id, params), "tvshow")

    def get_videodetails_by_externalid(self, extid, extid_type):
        """get metadata by external ID (like imdbid)"""
        params = {"external_source": extid_type, "language": KODI_LANGUAGE}
        results = self.get_data("find/%s" % extid, params)
        if results and results["movie_results"]:
            return self.get_movie_details(results["movie_results"][0]["id"])
        elif results and results["tv_results"]:
            return self.get_tvshow_details(results["tv_results"][0]["id"])
        return {}

    def get_data(self, endpoint, params):
        """helper method to get data from tmdb json API"""
        if self.api_key:
            # addon provided or personal api key
            params["api_key"] = self.api_key
            rate_limit = None
            expiration = datetime.timedelta(days=7)
        else:
            # fallback api key (rate limited !)
            params["api_key"] = "80246691939720672db3fc71c74e0ef2"
            # without personal (or addon specific) api key = rate limiting and older info from cache
            rate_limit = ("themoviedb.org", 5)
            expiration = datetime.timedelta(days=60)
        if sys.version_info.major == 3:
            cachestr = "tmdb.%s" % params.values()
        else:
            cachestr = "tmdb.%s" % params.itervalues()
        cache = self.cache.get(cachestr)
        if cache:
            # data obtained from cache
            result = cache
        else:
            # no cache, grab data from API
            url = u'https://api.themoviedb.org/3/%s' % endpoint
            result = get_json(url, params, ratelimit=rate_limit)
            # make sure that we have a plot value (if localized value fails, fallback to english)
            if result and "language" in params and "overview" in result:
                if not result["overview"] and params["language"] != "en":
                    params["language"] = "en"
                    result2 = get_json(url, params)
                    if result2 and result2.get("overview"):
                        result = result2
            self.cache.set(url, result, expiration=expiration)
        return result

    def map_details(self, data, media_type):
        """helper method to map the details received from tmdb to kodi compatible formatting"""
        if not data:
            return {}
        details = {}
        details["tmdb_id"] = data["id"]
        details["rating"] = data["vote_average"]
        details["votes"] = data["vote_count"]
        details["rating.tmdb"] = data["vote_average"]
        details["votes.tmdb"] = data["vote_count"]
        details["popularity"] = data["popularity"]
        details["popularity.tmdb"] = data["popularity"]
        details["plot"] = data["overview"]
        details["genre"] = [item["name"] for item in data["genres"]]
        details["homepage"] = data["homepage"]
        details["status"] = data["status"]
        details["cast"] = []
        details["castandrole"] = []
        details["writer"] = []
        details["director"] = []
        details["media_type"] = media_type
        # cast
        if "credits" in data:
            if "cast" in data["credits"]:
                for cast_member in data["credits"]["cast"]:
                    cast_thumb = ""
                    if cast_member["profile_path"]:
                        cast_thumb = "https://image.tmdb.org/t/p/original%s" % cast_member["profile_path"]
                    details["cast"].append({"name": cast_member["name"], "role": cast_member["character"],
                                            "thumbnail": cast_thumb})
                    details["castandrole"].append((cast_member["name"], cast_member["character"]))
            # crew (including writers and directors)
            if "crew" in data["credits"]:
                for crew_member in data["credits"]["crew"]:
                    cast_thumb = ""
                    if crew_member["profile_path"]:
                        cast_thumb = "https://image.tmdb.org/t/p/original%s" % crew_member["profile_path"]
                    if crew_member["job"] in ["Author", "Writer"]:
                        details["writer"].append(crew_member["name"])
                    if crew_member["job"] in ["Producer", "Executive Producer"]:
                        details["director"].append(crew_member["name"])
                    if crew_member["job"] in ["Producer", "Executive Producer", "Author", "Writer"]:
                        details["cast"].append({"name": crew_member["name"], "role": crew_member["job"],
                                                "thumbnail": cast_thumb})
        # artwork
        details["art"] = {}
        if data.get("images"):
            if data["images"].get("backdrops"):
                fanarts = self.get_best_images(data["images"]["backdrops"])
                details["art"]["fanarts"] = fanarts
                details["art"]["fanart"] = fanarts[0] if fanarts else ""
            if data["images"].get("posters"):
                posters = self.get_best_images(data["images"]["posters"])
                details["art"]["posters"] = posters
                details["art"]["poster"] = posters[0] if posters else ""
        if not details["art"].get("poster") and data.get("poster_path"):
            details["art"]["poster"] = "https://image.tmdb.org/t/p/original%s" % data["poster_path"]
        if not details["art"].get("fanart") and data.get("backdrop_path"):
            details["art"]["fanart"] = "https://image.tmdb.org/t/p/original%s" % data["backdrop_path"]
        # movies only
        if media_type == "movie":
            details["title"] = data["title"]
            details["originaltitle"] = data["original_title"]
            if data["belongs_to_collection"]:
                details["set"] = data["belongs_to_collection"].get("name", "")
            if data.get("release_date"):
                details["premiered"] = data["release_date"]
                details["year"] = try_parse_int(data["release_date"].split("-")[0])
            details["tagline"] = data["tagline"]
            if data["runtime"]:
                details["runtime"] = data["runtime"] * 60
            details["imdbnumber"] = data["imdb_id"]
            details["budget"] = data["budget"]
            details["budget.formatted"] = int_with_commas(data["budget"])
            details["revenue"] = data["revenue"]
            details["revenue.formatted"] = int_with_commas(data["revenue"])
            if data.get("production_companies"):
                details["studio"] = [item["name"] for item in data["production_companies"]]
            if data.get("production_countries"):
                details["country"] = [item["name"] for item in data["production_countries"]]
            if data.get("keywords"):
                details["tag"] = [item["name"] for item in data["keywords"]["keywords"]]
        # tvshows only
        if media_type == "tvshow":
            details["title"] = data["name"]
            details["originaltitle"] = data["original_name"]
            if data.get("created_by"):
                details["director"] += [item["name"] for item in data["created_by"]]
            if data.get("episode_run_time"):
                details["runtime"] = data["episode_run_time"][0] * 60
            if data.get("first_air_date"):
                details["premiered"] = data["first_air_date"]
                details["year"] = try_parse_int(data["first_air_date"].split("-")[0])
            if "last_air_date" in data:
                details["lastaired"] = data["last_air_date"]
            if data.get("networks"):
                details["studio"] = [item["name"] for item in data["networks"]]
            if "origin_country" in data:
                details["country"] = data["origin_country"]
            if "number_of_seasons" in data:
                details["Seasons"] = data["number_of_seasons"]
            if "number_of_episodes" in data:
                details["Episodes"] = data["number_of_episodes"]
            if data.get("seasons"):
                tmdboverviewdetails = data["seasons"]
                seasons = []
                for count, item in enumerate(tmdboverviewdetails):
                    seasons.append(item["overview"])
                    details["seasons.formatted.%s" % count] = "%s %s[CR]%s[CR]" % (item["name"], item["air_date"], item["overview"])
                details["seasons.formatted"] = "[CR]".join(seasons)
            if data.get("external_ids"):
                details["imdbnumber"] = data["external_ids"].get("imdb_id", "")
                details["tvdb_id"] = data["external_ids"].get("tvdb_id", "")
            if "results" in data["keywords"]:
                details["tag"] = [item["name"] for item in data["keywords"]["results"]]
        # trailer
        for video in data["videos"]["results"]:
            if video["site"] == "YouTube" and video["type"] == "Trailer":
                details["trailer"] = 'plugin://plugin.video.youtube/?action=play_video&videoid=%s' % video["key"]
                break
        return details

    @staticmethod
    def get_best_images(images):
        """get the best 5 images based on number of likes and the language"""
        for image in images:
            score = 0
            score += image["vote_count"]
            score += image["vote_average"] * 10
            score += image["height"]
            if "iso_639_1" in image:
                if image["iso_639_1"] == KODI_LANGUAGE:
                    score += 1000
            image["score"] = score
            if not image["file_path"].startswith("https"):
                image["file_path"] = "https://image.tmdb.org/t/p/original%s" % image["file_path"]
        images = sorted(images, key=itemgetter("score"), reverse=True)
        return [image["file_path"] for image in images]

    @staticmethod
    def select_best_match(results, prefyear="", preftype="", preftitle="", manual_select=False):
        """helper to select best match or let the user manually select the best result from the search"""
        details = {}
        # score results if one or more preferences are given
        if results and (prefyear or preftype or preftitle):
            newdata = []
            preftitle = preftitle.lower()
            for item in results:
                item["score"] = 0
                itemtitle = item["title"] if item.get("title") else item["name"]
                itemtitle = itemtitle.lower()
                itemorgtitle = item["original_title"] if item.get("original_title") else item["original_name"]
                itemorgtitle = itemorgtitle.lower()

                # high score if year matches
                if prefyear:
                    if item.get("first_air_date") and prefyear in item["first_air_date"]:
                        item["score"] += 800  # matches preferred year
                    if item.get("release_date") and prefyear in item["release_date"]:
                        item["score"] += 800  # matches preferred year

                # find exact match on title
                if preftitle and preftitle == itemtitle:
                    item["score"] += 1000  # exact match!
                if preftitle and preftitle == itemorgtitle:
                    item["score"] += 1000  # exact match!

                # match title by replacing some characters
                if preftitle and get_compare_string(preftitle) == get_compare_string(itemtitle):
                    item["score"] += 750
                if preftitle and get_compare_string(preftitle) == get_compare_string(itemorgtitle):
                    item["score"] += 750

                # add SequenceMatcher score to the results
                if preftitle:
                    stringmatchscore = SM(None, preftitle, itemtitle).ratio(
                    ) + SM(None, preftitle, itemorgtitle).ratio()
                    if stringmatchscore > 1.6:
                        item["score"] += stringmatchscore * 250

                # higher score if result ALSO matches our preferred type or native language
                # (only when we already have a score)
                if item["score"]:
                    if preftype and (item["media_type"] in preftype) or (preftype in item["media_type"]):
                        item["score"] += 250  # matches preferred type
                    if item["original_language"] == KODI_LANGUAGE:
                        item["score"] += 500  # native language!
                    if KODI_LANGUAGE.upper() in item.get("origin_country", []):
                        item["score"] += 500  # native language!
                    if KODI_LANGUAGE in item.get("languages", []):
                        item["score"] += 500  # native language!

                if item["score"] > 500 or manual_select:
                    newdata.append(item)
            results = sorted(newdata, key=itemgetter("score"), reverse=True)

        if results and manual_select:
            # show selectdialog to manually select the item
            results_list = []
            for item in results:
                title = item["name"] if "name" in item else item["title"]
                if item.get("premiered"):
                    year = item["premiered"].split("-")[0]
                else:
                    year = item.get("first_air_date", "").split("-")[0]
                if item["poster_path"]:
                    thumb = "https://image.tmdb.org/t/p/original%s" % item["poster_path"]
                else:
                    thumb = ""
                label = "%s (%s) - %s" % (title, year, item["media_type"])
                listitem = xbmcgui.ListItem(label=label, label2=item["overview"])
                listitem.setArt({'icon': thumb})
                results_list.append(listitem)
            if manual_select and results_list:
                dialog = DialogSelect("DialogSelect.xml", "", listing=results_list, window_title="%s - TMDB"
                                      % xbmc.getLocalizedString(283))
                dialog.doModal()
                selected_item = dialog.result
                del dialog
                if selected_item != -1:
                    details = results[selected_item]
                else:
                    results = []

        if not details and results:
            # just grab the first item as best match
            details = results[0]
        return details
