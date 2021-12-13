#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    Returns complete (nicely formatted) information about the movieset and it's movies
"""

import os, sys
if sys.version_info.major == 3:
    from .kodi_constants import FIELDS_MOVIES
    from .utils import get_duration, get_clean_image, extend_dict
    from urllib.parse import quote_plus
else:
    from kodi_constants import FIELDS_MOVIES
    from utils import get_duration, get_clean_image, extend_dict
    from urllib import quote_plus
from operator import itemgetter
import xbmc


def get_moviesetdetails(metadatautils, title, set_id):
    """Returns complete (nicely formatted) information about the movieset and it's movies"""
    details = {}
    # try to get from cache first
    # use checksum compare based on playcounts because moviesets do not get refreshed automatically
    movieset = metadatautils.kodidb.movieset(set_id, ["playcount"])
    cache_str = "MovieSetDetails.%s" % set_id
    cache_checksum = "%s.%s" % (set_id, metadatautils.studiologos_path)
    if movieset and len(movieset["movies"]) < 50:
        for movie in movieset["movies"]:
            cache_checksum += "%s" % movie["playcount"]
        cache = metadatautils.cache.get(cache_str, checksum=cache_checksum)
        if cache:
            return cache
        # grab all details online and from kodi dbid
        details = get_online_setdata(metadatautils, title)
        details = extend_dict(details, get_kodidb_setdata(metadatautils, set_id))
        if not details.get("plot"):
            details["plot"] = details["plots"]
        details["extendedplot"] = details["titles"] + u"[CR]" + details["plot"]
        all_fanarts = details["art"]["fanarts"]
        efa_path = "plugin://script.skin.helper.service/?action=extrafanart&fanarts=%s" % quote_plus(repr(all_fanarts))
        details["art"]["extrafanart"] = efa_path
        for count, fanart in enumerate(all_fanarts):
            details["art"]["ExtraFanArt.%s" % count] = fanart
    metadatautils.cache.set(cache_str, details, checksum=cache_checksum)
    return details


def get_online_setdata(metadatautils, title):
    """get moviesetdetails from TMDB and fanart.tv"""
    details = metadatautils.tmdb.search_movieset(title)
    if details:
        # append images from fanart.tv
        details["art"] = extend_dict(
            details["art"],
            metadatautils.fanarttv.movie(details["tmdb_id"]),
            ["poster", "fanart", "clearlogo", "clearart"])
    return details

# pylint: disable-msg=too-many-local-variables


def get_kodidb_setdata(metadatautils, set_id):
    """get moviesetdetails from Kodi DB"""
    details = {}
    movieset = metadatautils.kodidb.movieset(set_id, FIELDS_MOVIES)
    count = 0
    runtime = 0
    unwatchedcount = 0
    watchedcount = 0
    runtime = 0
    writer = []
    director = []
    genre = []
    countries = []
    studio = []
    years = []
    plot = ""
    title_list = ""
    total_movies = len(movieset['movies'])
    title_header = "[B]%s %s[/B][CR]" % (total_movies, xbmc.getLocalizedString(20342))
    all_fanarts = []
    details["art"] = movieset["art"]
    movieset_movies = sorted(movieset['movies'], key=itemgetter("year"))
    for count, item in enumerate(movieset_movies):
        if item["playcount"] == 0:
            unwatchedcount += 1
        else:
            watchedcount += 1

        # generic labels
        for label in ["label", "plot", "year", "rating"]:
            details['%s.%s' % (count, label)] = item[label]
        details["%s.DBID" % count] = item["movieid"]
        details["%s.duration" % count] = item['runtime'] / 60

        # art labels
        art = item['art']
        for label in ["poster", "fanart", "landscape", "clearlogo", "clearart", "banner", "discart"]:
            if art.get(label):
                details['%s.art.%s' % (count, label)] = get_clean_image(art[label])
                if not movieset["art"].get(label):
                    movieset["art"][label] = get_clean_image(art[label])
        all_fanarts.append(get_clean_image(art.get("fanart")))

        # streamdetails
        if item.get('streamdetails', ''):
            streamdetails = item["streamdetails"]
            audiostreams = streamdetails.get('audio', [])
            videostreams = streamdetails.get('video', [])
            subtitles = streamdetails.get('subtitle', [])
            if len(videostreams) > 0:
                stream = videostreams[0]
                height = stream.get("height", "")
                width = stream.get("width", "")
                if height and width:
                    resolution = ""
                    if width <= 720 and height <= 480:
                        resolution = "480"
                    elif width <= 768 and height <= 576:
                        resolution = "576"
                    elif width <= 960 and height <= 544:
                        resolution = "540"
                    elif width <= 1280 and height <= 720:
                        resolution = "720"
                    elif width <= 1920 and height <= 1080:
                        resolution = "1080"
                    elif width * height >= 6000000:
                        resolution = "4K"
                    details["%s.resolution" % count] = resolution
                details["%s.Codec" % count] = stream.get("codec", "")
                if stream.get("aspect", ""):
                    details["%s.aspectratio" % count] = round(stream["aspect"], 2)
            if len(audiostreams) > 0:
                # grab details of first audio stream
                stream = audiostreams[0]
                details["%s.audiocodec" % count] = stream.get('codec', '')
                details["%s.audiochannels" % count] = stream.get('channels', '')
                details["%s.audiolanguage" % count] = stream.get('language', '')
            if len(subtitles) > 0:
                # grab details of first subtitle
                details["%s.SubTitle" % count] = subtitles[0].get('language', '')

        title_list += "%s (%s)[CR]" % (item['label'], item['year'])
        if item['plotoutline']:
            plot += "[B]%s (%s)[/B][CR]%s[CR][CR]" % (item['label'], item['year'], item['plotoutline'])
        else:
            plot += "[B]%s (%s)[/B][CR]%s[CR][CR]" % (item['label'], item['year'], item['plot'])
        runtime += item['runtime']
        if item.get("writer"):
            writer += [w for w in item["writer"] if w and w not in writer]
        if item.get("director"):
            director += [d for d in item["director"] if d and d not in director]
        if item.get("genre"):
            genre += [g for g in item["genre"] if g and g not in genre]
        if item.get("country"):
            countries += [c for c in item["country"] if c and c not in countries]
        if item.get("studio"):
            studio += [s for s in item["studio"] if s and s not in studio]
        years.append(str(item['year']))
    details["plots"] = plot
    if total_movies > 1:
        details["extendedplots"] = title_header + title_list + "[CR]" + plot
    else:
        details["extendedplots"] = plot
    details["titles"] = title_list
    details["runtime"] = runtime / 60
    details.update(get_duration(runtime / 60))
    details["writer"] = writer
    details["director"] = director
    details["genre"] = genre
    details["studio"] = studio
    details["years"] = years
    if len(years) > 1:
        details["year"] = "%s - %s" % (years[0], years[-1])
    else:
        details["year"] = years[0] if years else ""
    details["country"] = countries
    details["watchedcount"] = str(watchedcount)
    details["unwatchedcount"] = str(unwatchedcount)
    details.update(metadatautils.studiologos.get_studio_logo(studio, metadatautils.studiologos_path))
    details["count"] = total_movies
    details["art"]["fanarts"] = all_fanarts
    return details
