#!/usr/bin/python
# -*- coding: utf-8 -*-

"""get metadata from omdb"""
import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, get_xml, formatted_number, int_with_commas, try_parse_int, KODI_LANGUAGE, ADDON_ID
else:
    from utils import get_json, get_xml, formatted_number, int_with_commas, try_parse_int, KODI_LANGUAGE, ADDON_ID
from simplecache import use_cache
import arrow
import xbmc
import xbmcaddon


class Omdb(object):
    """get metadata from omdb"""
    api_key = None  # public var to be set by the calling addon

    def __init__(self, simplecache=None):
        """Initialize - optionaly provide simplecache object"""
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache
        addon = xbmcaddon.Addon(id=ADDON_ID)
        api_key = addon.getSetting("omdbapi_apikey")
        if api_key:
            self.api_key = api_key
        del addon

    @use_cache(14)
    def get_details_by_imdbid(self, imdb_id):
        """get omdb details by providing an imdb id"""
        params = {"i": imdb_id}
        data = self.get_data(params)
        return self.map_details(data) if data else None

    @use_cache(14)
    def get_details_by_title(self, title, year="", media_type=""):
        """ get omdb details by title
            title --> The title of the media to look for (required)
            year (str/int)--> The year of the media (optional, better results when provided)
            media_type --> The type of the media: movie/tvshow (optional, better results of provided)
        """
        if "movie" in media_type:
            media_type = "movie"
        elif media_type in ["tvshows", "tvshow"]:
            media_type = "series"
        params = {"t": title, "y": year, "type": media_type}
        data = self.get_data(params)
        return self.map_details(data) if data else None

    @use_cache(14)
    def get_data(self, params):
        """helper method to get data from omdb json API"""
        base_url = 'http://www.omdbapi.com/'
        params["plot"] = "full"
        if self.api_key:
            params["apikey"] = self.api_key
            rate_limit = None
        else:
            # rate limited api key !
            params["apikey"] = "d4d53b9a"
            rate_limit = ("omdbapi.com", 2)
        params["r"] = "xml"
        params["tomatoes"] = "true"
        return get_xml(base_url, params, ratelimit=rate_limit)

    @staticmethod
    def map_details(data):
        """helper method to map the details received from omdb to kodi compatible format"""
        result = {}
        if sys.version_info.major == 3:
            for key, value in data.items():
                # filter the N/A values
                if value in ["N/A", "NA"] or not value:
                    continue
                if key == "title":
                    result["title"] = value
                elif key == "year":
                    try:
                        result["year"] = try_parse_int(value.split("-")[0])
                    except Exception:
                        result["year"] = value
                elif key == "rated":
                    result["mpaa"] = value.replace("Rated", "")
                elif key == "released":
                    date_time = arrow.get(value, "DD MMM YYYY")
                    result["premiered"] = date_time.strftime(xbmc.getRegion("dateshort"))
                    try:
                        result["premiered.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
                    except Exception:
                        result["premiered.formatted"] = value
                elif key == "runtime":
                    result["runtime"] = try_parse_int(value.replace(" min", "")) * 60
                elif key == "genre":
                    result["genre"] = value.split(", ")
                elif key == "director":
                    result["director"] = value.split(", ")
                elif key == "writer":
                    result["writer"] = value.split(", ")
                elif key == "country":
                    result["country"] = value.split(", ")
                elif key == "awards":
                    result["awards"] = value
                elif key == "poster":
                    result["thumbnail"] = value
                    result["art"] = {}
                    result["art"]["thumb"] = value
                elif key == "imdbVotes":
                    result["votes.imdb"] = value
                    result["votes"] = try_parse_int(value.replace(",", ""))
                elif key == "imdbRating":
                    result["rating.imdb"] = value
                    result["rating"] = float(value)
                    result["rating.percent.imdb"] = "%s" % (try_parse_int(float(value) * 10))
                elif key == "metascore":
                    result["metacritic.rating"] = value
                    result["metacritic.rating.percent"] = "%s" % value
                elif key == "imdbID":
                    result["imdbnumber"] = value
                elif key == "BoxOffice":
                    result["boxoffice"] = value
                elif key == "DVD":
                    date_time = arrow.get(value, "DD MMM YYYY")
                    result["dvdrelease"] = date_time.format('YYYY-MM-DD')
                    result["dvdrelease.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
                elif key == "Production":
                    result["studio"] = value.split(", ")
                elif key == "Website":
                    result["homepage"] = value
                elif key == "plot":
                    result["plot"] = value
                    result["imdb.plot"] = value
                elif key == "type":
                    if value == "series":
                        result["type"] = "tvshow"
                    else:
                        result["type"] = value
                    result["media_type"] = result["type"]
            # rotten tomatoes
                elif key == "tomatoMeter":
                    result["rottentomatoes.meter"] = value
                    result["rottentomatoesmeter"] = value
                elif key == "tomatoImage":
                    result["rottentomatoes.image"] = value
                elif key == "tomatoRating":
                    result["rottentomatoes.rating"] = value
                    result["rottentomatoes.rating.percent"] = "%s" % (try_parse_int(float(value) * 10))
                    result["rating.rt"] = value
                elif key == "tomatoReviews":
                    result["rottentomatoes.reviews"] = formatted_number(value)
                elif key == "tomatoFresh":
                    result["rottentomatoes.fresh"] = value
                elif key == "tomatoRotten":
                    result["rottentomatoes.rotten"] = value
                elif key == "tomatoConsensus":
                    result["rottentomatoes.consensus"] = value
                elif key == "tomatoUserMeter":
                    result["rottentomatoes.usermeter"] = value
                elif key == "tomatoUserRating":
                    result["rottentomatoes.userrating"] = value
                    result["rottentomatoes.userrating.percent"] = "%s" % (try_parse_int(float(value) * 10))
                elif key == "tomatoUserReviews":
                    result["rottentomatoes.userreviews"] = int_with_commas(value)
                elif key == "tomatoeURL":
                    result["rottentomatoes.url"] = value
        else:
            for key, value in data.iteritems():
                # filter the N/A values
                if value in ["N/A", "NA"] or not value:
                    continue
                if key == "title":
                    result["title"] = value
                elif key == "Year":
                    try:
                        result["year"] = try_parse_int(value.split("-")[0])
                    except Exception:
                        result["year"] = value
                elif key == "rated":
                    result["mpaa"] = value.replace("Rated", "")
                elif key == "released":
                    date_time = arrow.get(value, "DD MMM YYYY")
                    result["premiered"] = date_time.strftime(xbmc.getRegion("dateshort"))
                    try:
                        result["premiered.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
                    except Exception:
                        result["premiered.formatted"] = value
                elif key == "runtime":
                    result["runtime"] = try_parse_int(value.replace(" min", "")) * 60
                elif key == "genre":
                    result["genre"] = value.split(", ")
                elif key == "director":
                    result["director"] = value.split(", ")
                elif key == "writer":
                    result["writer"] = value.split(", ")
                elif key == "country":
                    result["country"] = value.split(", ")
                elif key == "awards":
                    result["awards"] = value
                elif key == "poster":
                    result["thumbnail"] = value
                    result["art"] = {}
                    result["art"]["thumb"] = value
                elif key == "imdbVotes":
                    result["votes.imdb"] = value
                    result["votes"] = try_parse_int(value.replace(",", ""))
                elif key == "imdbRating":
                    result["rating.imdb"] = value
                    result["rating"] = float(value)
                    result["rating.percent.imdb"] = "%s" % (try_parse_int(float(value) * 10))
                elif key == "metascore":
                    result["metacritic.rating"] = value
                    result["metacritic.rating.percent"] = "%s" % value
                elif key == "imdbID":
                    result["imdbnumber"] = value
                elif key == "BoxOffice":
                    result["boxoffice"] = value
                elif key == "DVD":
                    date_time = arrow.get(value, "DD MMM YYYY")
                    result["dvdrelease"] = date_time.format('YYYY-MM-DD')
                    result["dvdrelease.formatted"] = date_time.format('DD MMM YYYY', locale=KODI_LANGUAGE)
                elif key == "Production":
                    result["studio"] = value.split(", ")
                elif key == "Website":
                    result["homepage"] = value
                elif key == "plot":
                    result["plot"] = value
                    result["imdb.plot"] = value
                elif key == "type":
                    if value == "series":
                        result["type"] = "tvshow"
                    else:
                        result["type"] = value
                    result["media_type"] = result["type"]
            # rotten tomatoes
                elif key == "tomatoMeter":
                    result["rottentomatoes.meter"] = value
                    result["rottentomatoesmeter"] = value
                elif key == "tomatoImage":
                    result["rottentomatoes.image"] = value
                elif key == "tomatoRating":
                    result["rottentomatoes.rating"] = value
                    result["rottentomatoes.rating.percent"] = "%s" % (try_parse_int(float(value) * 10))
                    result["rating.rt"] = value
                elif key == "tomatoReviews":
                    result["rottentomatoes.reviews"] = formatted_number(value)
                elif key == "tomatoFresh":
                    result["rottentomatoes.fresh"] = value
                elif key == "tomatoRotten":
                    result["rottentomatoes.rotten"] = value
                elif key == "tomatoConsensus":
                    result["rottentomatoes.consensus"] = value
                elif key == "tomatoUserMeter":
                    result["rottentomatoes.usermeter"] = value
                elif key == "tomatoUserRating":
                    result["rottentomatoes.userrating"] = value
                    result["rottentomatoes.userrating.percent"] = "%s" % (try_parse_int(float(value) * 10))
                elif key == "tomatoUserReviews":
                    result["rottentomatoes.userreviews"] = int_with_commas(value)
                elif key == "tomatoeURL":
                    result["rottentomatoes.url"] = value
        return result
