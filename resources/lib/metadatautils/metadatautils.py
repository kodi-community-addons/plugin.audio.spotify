#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    Provides all kind of mediainfo for kodi media, returned as dict with details
'''

import os, sys
import helpers.kodi_constants as kodi_constants
from helpers.utils import log_msg, ADDON_ID
from simplecache import use_cache, SimpleCache
import xbmcvfs

if sys.version_info.major == 3:
    from urllib.parse import quote_plus
else:
    from urllib import quote_plus


class MetadataUtils(object):
    '''
        Provides all kind of mediainfo for kodi media, returned as dict with details
    '''
    _audiodb, _addon, _close_called, _omdb, _kodidb, _tmdb, _fanarttv, _channellogos = [None] * 8
    _imdb, _google, _studiologos, _animatedart, _thetvdb, _musicart, _pvrart, _lastfm = [None] * 8
    _studiologos_path, _process_method_on_list, _detect_plugin_content, _get_streamdetails = [None] * 4
    _extend_dict, _get_clean_image, _get_duration, _get_extrafanart, _get_extraposter, _get_moviesetdetails = [None] * 6
    cache = None


    def __init__(self):
        '''Initialize and load all our helpers'''
        self.cache = SimpleCache()
        log_msg("Initialized")

    @use_cache(14)
    def get_extrafanart(self, file_path):
        '''helper to retrieve the extrafanart path for a kodi media item'''
        log_msg("metadatautils get_extrafanart called for %s" % file_path)
        if not self._get_extrafanart:
            from helpers.extrafanart import get_extrafanart
            self._get_extrafanart = get_extrafanart
        return self._get_extrafanart(file_path)

    @use_cache(14)
    def get_extraposter(self, file_path):
        '''helper to retrieve the extraposter path for a kodi media item'''
        if not self._get_extraposter:
            from helpers.extraposter import get_extraposter
            self._get_extraposter = get_extraposter
        return self._get_extraposter(file_path)

    def get_music_artwork(self, artist, album="", track="", disc="", ignore_cache=False, flush_cache=False):
        '''method to get music artwork for the goven artist/album/song'''
        return self.musicart.get_music_artwork(
            artist, album, track, disc, ignore_cache=ignore_cache, flush_cache=flush_cache)

    def music_artwork_options(self, artist, album="", track="", disc=""):
        '''options for music metadata for specific item'''
        return self.musicart.music_artwork_options(artist, album, track, disc)

    @use_cache(7)
    def get_extended_artwork(self, imdb_id="", tvdb_id="", tmdb_id="", media_type=""):
        '''get extended artwork for the given imdbid or tvdbid'''
        result = None
        if "movie" in media_type and tmdb_id:
            result = self.fanarttv.movie(tmdb_id)
        elif "movie" in media_type and imdb_id:
            # prefer local artwork
            local_details = self.kodidb.movie_by_imdbid(imdb_id)
            if local_details:
                result = local_details["art"]
            result = self.extend_dict(result, self.fanarttv.movie(imdb_id))
        elif media_type in ["tvshow", "tvshows", "seasons", "episodes"]:
            if not tvdb_id:
                if imdb_id and not imdb_id.startswith("tt"):
                    tvdb_id = imdb_id
                elif imdb_id:
                    tvdb_id = self.thetvdb.get_series_by_imdb_id(imdb_id).get("tvdb_id")
            if tvdb_id:
                # prefer local artwork
                local_details = self.kodidb.tvshow_by_imdbid(tvdb_id)
                if local_details:
                    result = local_details["art"]
                elif imdb_id and imdb_id != tvdb_id:
                    local_details = self.kodidb.tvshow_by_imdbid(imdb_id)
                    if local_details:
                        result = local_details["art"]
                result = self.extend_dict(result, self.fanarttv.tvshow(tvdb_id))
        # add additional art with special path
        if result:
            result = {"art": result}
            for arttype in ["fanarts", "posters", "clearlogos", "banners", "discarts", "cleararts", "characterarts"]:
                if result["art"].get(arttype):
                    result["art"][arttype] = "plugin://script.skin.helper.service/"\
                        "?action=extrafanart&fanarts=%s" % quote_plus(repr(result["art"][arttype]))
        return result

    @use_cache(90)
    def get_tmdb_details(self, imdb_id="", tvdb_id="", title="", year="", media_type="",
                         preftype="", manual_select=False, ignore_cache=False):
        '''returns details from tmdb'''
        result = {}
        if imdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                imdb_id, "imdb_id")
        elif tvdb_id:
            result = self.tmdb.get_videodetails_by_externalid(
                tvdb_id, "tvdb_id")
        elif title and media_type in ["movies", "setmovies", "movie"]:
            result = self.tmdb.search_movie(
                title, year, manual_select=manual_select, ignore_cache=ignore_cache)
        elif title and media_type in ["tvshows", "tvshow"]:
            result = self.tmdb.search_tvshow(
                title, year, manual_select=manual_select, ignore_cache=ignore_cache)
        elif title:
            result = self.tmdb.search_video(
                title, year, preftype=preftype, manual_select=manual_select, ignore_cache=ignore_cache)
        if result and result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result and result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(self.get_duration(result["runtime"]))
        return result

    @use_cache(90)
    def get_moviesetdetails(self, title, set_id):
        '''get a nicely formatted dict of the movieset details which we can for example set as window props'''
        # get details from tmdb
        if not self._get_moviesetdetails:
            from helpers.moviesetdetails import get_moviesetdetails
            self._get_moviesetdetails = get_moviesetdetails
        return self._get_moviesetdetails(self, title, set_id)

    @use_cache(14)
    def get_streamdetails(self, db_id, media_type, ignore_cache=False):
        '''get a nicely formatted dict of the streamdetails'''
        if not self._get_streamdetails:
            from helpers.streamdetails import get_streamdetails
            self._get_streamdetails = get_streamdetails
        return self._get_streamdetails(self.kodidb, db_id, media_type)

    def get_pvr_artwork(self, title, channel="", genre="", manual_select=False, ignore_cache=False):
        '''get artwork and mediadetails for PVR entries'''
        return self.pvrart.get_pvr_artwork(
            title, channel, genre, manual_select=manual_select, ignore_cache=ignore_cache)

    def pvr_artwork_options(self, title, channel="", genre=""):
        '''options for pvr metadata for specific item'''
        return self.pvrart.pvr_artwork_options(title, channel, genre)

    def get_channellogo(self, channelname):
        '''get channellogo for the given channel name'''
        return self.channellogos.get_channellogo(channelname)

    def get_studio_logo(self, studio):
        '''get studio logo for the given studio'''
        # dont use cache at this level because of changing logospath
        return self.studiologos.get_studio_logo(studio, self.studiologos_path)

    @property
    def studiologos_path(self):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        return self._studiologos_path

    @studiologos_path.setter
    def studiologos_path(self, value):
        '''path to use to lookup studio logos, must be set by the calling addon'''
        self._studiologos_path = value

    def get_animated_artwork(self, imdb_id, manual_select=False, ignore_cache=False):
        '''get animated artwork, perform extra check if local version still exists'''
        artwork = self.animatedart.get_animated_artwork(
            imdb_id, manual_select=manual_select, ignore_cache=ignore_cache)
        if not (manual_select or ignore_cache):
            refresh_needed = False
            if artwork.get("animatedposter") and not xbmcvfs.exists(
                    artwork["animatedposter"]):
                refresh_needed = True
            if artwork.get("animatedfanart") and not xbmcvfs.exists(
                    artwork["animatedfanart"]):
                refresh_needed = True

        return {"art": artwork}

    @use_cache(90)
    def get_omdb_info(self, imdb_id="", title="", year="", content_type=""):
        '''Get (kodi compatible formatted) metadata from OMDB, including Rotten tomatoes details'''
        title = title.split(" (")[0]  # strip year appended to title
        result = {}
        if imdb_id:
            result = self.omdb.get_details_by_imdbid(imdb_id)
        elif title and content_type in ["seasons", "season", "episodes", "episode", "tvshows", "tvshow"]:
            result = self.omdb.get_details_by_title(title, "", "tvshows")
        elif title and year:
            result = self.omdb.get_details_by_title(title, year, content_type)
        if result and result.get("status"):
            result["status"] = self.translate_string(result["status"])
        if result and result.get("runtime"):
            result["runtime"] = result["runtime"] / 60
            result.update(self.get_duration(result["runtime"]))
        return result

    def get_top250_rating(self, imdb_id):
        '''get the position in the IMDB top250 for the given IMDB ID'''
        return self.imdb.get_top250_rating(imdb_id)

    @use_cache(14)
    def get_duration(self, duration):
        '''helper to get a formatted duration'''
        if not self._get_duration:
            from helpers.utils import get_duration
            self._get_duration = get_duration
        if sys.version_info.major == 3:
            if isinstance(duration, str) and ":" in duration:
                dur_lst = duration.split(":")
                return {
                    "Duration": "%s:%s" % (dur_lst[0], dur_lst[1]),
                    "Duration.Hours": dur_lst[0],
                    "Duration.Minutes": dur_lst[1],
                    "Runtime": int(dur_lst[0]) * 60 + int(dur_lst[1]),
                }
            else:
                return self._get_duration(duration)
        else:
            if isinstance(duration, (str, unicode)) and ":" in duration:
                dur_lst = duration.split(":")
                return {
                    "Duration": "%s:%s" % (dur_lst[0], dur_lst[1]),
                    "Duration.Hours": dur_lst[0],
                    "Duration.Minutes": dur_lst[1],
                    "Runtime": str((int(dur_lst[0]) * 60) + int(dur_lst[1])),
                }
            else:
                return self._get_duration(duration)

    @use_cache(2)
    def get_tvdb_details(self, imdbid="", tvdbid=""):
        '''get metadata from tvdb by providing a tvdbid or tmdbid'''
        result = {}
        self.thetvdb.days_ahead = 365
        if not tvdbid and imdbid and not imdbid.startswith("tt"):
            # assume imdbid is actually a tvdbid...
            tvdbid = imdbid
        if tvdbid:
            result = self.thetvdb.get_series(tvdbid)
        elif imdbid:
            result = self.thetvdb.get_series_by_imdb_id(imdbid)
        if result:
            if result["status"] == "Continuing":
                # include next episode info
                result["nextepisode"] = self.thetvdb.get_nextaired_episode(result["tvdb_id"])
            # include last episode info
            result["lastepisode"] = self.thetvdb.get_last_episode_for_series(result["tvdb_id"])
            result["status"] = self.translate_string(result["status"])
            if result.get("runtime"):
                result["runtime"] = result["runtime"] / 60
                result.update(self.get_duration(result["runtime"]))
        return result

    @use_cache(90)
    def get_imdbtvdb_id(self, title, content_type, year="", imdbid="", tvshowtitle=""):
        '''try to figure out the imdbnumber and/or tvdbid'''
        tvdbid = ""
        if content_type in ["seasons", "episodes"] or tvshowtitle:
            title = tvshowtitle
            content_type = "tvshows"
        if imdbid and not imdbid.startswith("tt"):
            if content_type in ["tvshows", "seasons", "episodes"]:
                tvdbid = imdbid
                imdbid = ""
        if not imdbid and year:
            omdb_info = self.get_omdb_info("", title, year, content_type)
            if omdb_info:
                imdbid = omdb_info.get("imdbnumber", "")
        if not imdbid:
            # repeat without year
            omdb_info = self.get_omdb_info("", title, "", content_type)
            if omdb_info:
                imdbid = omdb_info.get("imdbnumber", "")
        # return results
        return (imdbid, tvdbid)

    def translate_string(self, _str):
        '''translate the received english string from the various sources like tvdb, tmbd etc'''
        translation = _str
        _str = _str.lower()
        if "continuing" in _str:
            translation = self.addon.getLocalizedString(32037)
        elif "ended" in _str:
            translation = self.addon.getLocalizedString(32038)
        elif "released" in _str:
            translation = self.addon.getLocalizedString(32040)
        return translation

    def process_method_on_list(self, *args, **kwargs):
        '''expose our process_method_on_list method to public'''
        if not self._process_method_on_list:
            from helpers.utils import process_method_on_list
            self._process_method_on_list = process_method_on_list
        return self._process_method_on_list(*args, **kwargs)

    def detect_plugin_content(self, *args, **kwargs):
        '''expose our detect_plugin_content method to public'''
        if not self._detect_plugin_content:
            from helpers.utils import detect_plugin_content
            self._detect_plugin_content = detect_plugin_content
        return self._detect_plugin_content(*args, **kwargs)

    def extend_dict(self, *args, **kwargs):
        '''expose our extend_dict method to public'''
        if not self._extend_dict:
            from helpers.utils import extend_dict
            self._extend_dict = extend_dict
        return self._extend_dict(*args, **kwargs)

    def get_clean_image(self, *args, **kwargs):
        '''expose our get_clean_image method to public'''
        if not self._get_clean_image:
            from helpers.utils import get_clean_image
            self._get_clean_image = get_clean_image
        return self._get_clean_image(*args, **kwargs)

    @property
    def omdb(self):
        '''public omdb object - for lazy loading'''
        if not self._omdb:
            from helpers.omdb import Omdb
            self._omdb = Omdb(self.cache)
        return self._omdb

    @property
    def kodidb(self):
        '''public kodidb object - for lazy loading'''
        if not self._kodidb:
            from helpers.kodidb import KodiDb
            self._kodidb = KodiDb()
        return self._kodidb

    @property
    def tmdb(self):
        '''public Tmdb object - for lazy loading'''
        if not self._tmdb:
            from helpers.tmdb import Tmdb
            self._tmdb = Tmdb(self.cache)
        return self._tmdb

    @property
    def fanarttv(self):
        '''public FanartTv object - for lazy loading'''
        if not self._fanarttv:
            from helpers.fanarttv import FanartTv
            self._fanarttv = FanartTv(self.cache)
        return self._fanarttv

    @property
    def channellogos(self):
        '''public ChannelLogos object - for lazy loading'''
        if not self._channellogos:
            from helpers.channellogos import ChannelLogos
            self._channellogos = ChannelLogos(self.kodidb)
        return self._channellogos

    @property
    def imdb(self):
        '''public Imdb object - for lazy loading'''
        if not self._imdb:
            from helpers.imdb import Imdb
            self._imdb = Imdb(self.cache)
        return self._imdb

    @property
    def google(self):
        '''public GoogleImages object - for lazy loading'''
        if not self._google:
            from helpers.google import GoogleImages
            self._google = GoogleImages(self.cache)
        return self._google

    @property
    def studiologos(self):
        '''public StudioLogos object - for lazy loading'''
        if not self._studiologos:
            from helpers.studiologos import StudioLogos
            self._studiologos = StudioLogos(self.cache)
        return self._studiologos

    @property
    def animatedart(self):
        '''public AnimatedArt object - for lazy loading'''
        if not self._animatedart:
            from helpers.animatedart import AnimatedArt
            self._animatedart = AnimatedArt(self.cache, self.kodidb)
        return self._animatedart

    @property
    def thetvdb(self):
        '''public TheTvDb object - for lazy loading'''
        if not self._thetvdb:
            from thetvdb import TheTvDb
            self._thetvdb = TheTvDb()
        return self._thetvdb

    @property
    def musicart(self):
        '''public MusicArtwork object - for lazy loading'''
        if not self._musicart:
            from helpers.musicartwork import MusicArtwork
            self._musicart = MusicArtwork(self)
        return self._musicart

    @property
    def pvrart(self):
        '''public PvrArtwork object - for lazy loading'''
        if not self._pvrart:
            from helpers.pvrartwork import PvrArtwork
            self._pvrart = PvrArtwork(self)
        return self._pvrart

    @property
    def addon(self):
        '''public Addon object - for lazy loading'''
        if not self._addon:
            import xbmcaddon
            self._addon = xbmcaddon.Addon(ADDON_ID)
        return self._addon

    @property
    def lastfm(self):
        '''public LastFM object - for lazy loading'''
        if not self._lastfm:
            from helpers.lastfm import LastFM
            self._lastfm = LastFM()
        return self._lastfm

    @property
    def audiodb(self):
        '''public TheAudioDb object - for lazy loading'''
        if not self._audiodb:
            from helpers.theaudiodb import TheAudioDb
            self._audiodb = TheAudioDb()
        return self._audiodb

    def close(self):
        '''Cleanup instances'''
        self._close_called = True
        if self.cache:
            self.cache.close()
            del self.cache
        if self._addon:
            del self._addon
        if self._thetvdb:
            del self._thetvdb
        log_msg("Exited")

    def __del__(self):
        '''make sure close is called'''
        if not self._close_called:
            self.close()
