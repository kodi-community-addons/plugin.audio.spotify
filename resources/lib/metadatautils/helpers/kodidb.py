#!/usr/bin/python
# -*- coding: utf-8 -*-

"""get metadata from the kodi DB"""

import os, sys
import xbmc
import xbmcgui
import xbmcvfs
if sys.version_info.major == 3:
    from .utils import json, try_encode, log_msg, log_exception, get_clean_image, KODI_VERSION
    from .utils import try_parse_int, localdate_from_utc_string, localized_date_time
    from .kodi_constants import *
else: 
    from utils import json, try_encode, log_msg, log_exception, get_clean_image, KODI_VERSION
    from utils import try_parse_int, localdate_from_utc_string, localized_date_time
    from kodi_constants import *
from operator import itemgetter
import arrow


class KodiDb(object):
    """various methods and helpers to get data from kodi json api"""

    def movie(self, db_id):
        """get moviedetails from kodi db"""
        return self.get_json("VideoLibrary.GetMovieDetails", returntype="moviedetails",
                             fields=FIELDS_MOVIES, optparam=("movieid", try_parse_int(db_id)))

    def movies(self, sort=None, filters=None, limits=None, filtertype=None):
        """get moviedetails from kodi db"""
        return self.get_json("VideoLibrary.GetMovies", sort=sort, filters=filters,
                             fields=FIELDS_MOVIES, limits=limits, returntype="movies", filtertype=filtertype)

    def movie_by_imdbid(self, imdb_id):
        """gets a movie from kodidb by imdbid."""
        # apparently you can't filter on imdb so we have to do this the complicated way
        if KODI_VERSION > 16:
            # from Kodi 17 we have a uniqueid field instead of imdbnumber
            all_items = self.get_json('VideoLibrary.GetMovies', fields=["uniqueid"], returntype="movies")
            for item in all_items:
                if 'uniqueid' in item:
                    for item2 in item["uniqueid"].values():
                        if item2 == imdb_id:
                            return self.movie(item["movieid"])
        else:
            all_items = self.get_json('VideoLibrary.GetMovies', fields=["imdbnumber"], returntype="movies")
            for item in all_items:
                if item["imdbnumber"] == imdb_id:
                    return self.movie(item["movieid"])
        return {}

    def tvshow(self, db_id):
        """get tvshow from kodi db"""
        tvshow = self.get_json("VideoLibrary.GetTvShowDetails", returntype="tvshowdetails",
                               fields=FIELDS_TVSHOWS, optparam=("tvshowid", try_parse_int(db_id)))
        return self.tvshow_watchedcounts(tvshow)

    def tvshows(self, sort=None, filters=None, limits=None, filtertype=None):
        """get tvshows from kodi db"""
        tvshows = self.get_json("VideoLibrary.GetTvShows", sort=sort, filters=filters,
                                fields=FIELDS_TVSHOWS, limits=limits, returntype="tvshows", filtertype=filtertype)
        # append watched counters
        for tvshow in tvshows:
            self.tvshow_watchedcounts(tvshow)
        return tvshows

    def tvshow_by_imdbid(self, imdb_id):
        """gets a tvshow from kodidb by imdbid (or tvdbid)."""
        # apparently you can't filter on imdb so we have to do this the complicated way
        if KODI_VERSION > 16:
            # from Kodi 17 we have a uniqueid field instead of imdbnumber
            all_items = self.get_json('VideoLibrary.GetTvShows', fields=["uniqueid"], returntype="tvshows")
            for item in all_items:
                if 'uniqueid' in item:
                    for item2 in item["uniqueid"].values():
                        if item2 == imdb_id:
                            return self.tvshow(item["tvshowid"])
        else:
            # pre-kodi 17 approach
            all_items = self.get_json('VideoLibrary.GetTvShows', fields=["imdbnumber"], returntype="tvshows")
            for item in all_items:
                if item["imdbnumber"] == imdb_id:
                    return self.tvshow(item["tvshowid"])
        return {}

    def episode(self, db_id):
        """get episode from kodi db"""
        return self.get_json("VideoLibrary.GetEpisodeDetails", returntype="episodedetails",
                             fields=FIELDS_EPISODES, optparam=("episodeid", try_parse_int(db_id)))

    def episodes(self, sort=None, filters=None, limits=None, filtertype=None, tvshowid=None, fields=FIELDS_EPISODES):
        """get episodes from kodi db"""
        if tvshowid:
            params = ("tvshowid", try_parse_int(tvshowid))
        else:
            params = None
        return self.get_json("VideoLibrary.GetEpisodes", sort=sort, filters=filters, fields=fields,
                             limits=limits, returntype="episodes", filtertype=filtertype, optparam=params)

    def musicvideo(self, db_id):
        """get musicvideo from kodi db"""
        return self.get_json("VideoLibrary.GetMusicVideoDetails", returntype="musicvideodetails",
                             fields=FIELDS_MUSICVIDEOS, optparam=("musicvideoid", try_parse_int(db_id)))

    def musicvideos(self, sort=None, filters=None, limits=None, filtertype=None):
        """get musicvideos from kodi db"""
        return self.get_json("VideoLibrary.GetMusicVideos", sort=sort, filters=filters,
                             fields=FIELDS_MUSICVIDEOS, limits=limits, returntype="musicvideos", filtertype=filtertype)

    def movieset(self, db_id, include_set_movies_fields=""):
        """get movieset from kodi db"""
        if include_set_movies_fields:
            optparams = [("setid", try_parse_int(db_id)), ("movies", {"properties": include_set_movies_fields})]
        else:
            optparams = ("setid", try_parse_int(db_id))
        return self.get_json("VideoLibrary.GetMovieSetDetails", returntype="",
                             fields=["title", "art", "playcount"], optparam=optparams)

    def moviesets(self, sort=None, limits=None, include_set_movies=False):
        """get moviesetdetails from kodi db"""
        if include_set_movies:
            optparam = ("movies", {"properties": FIELDS_MOVIES})
        else:
            optparam = None
        return self.get_json("VideoLibrary.GetMovieSets", sort=sort,
                             fields=["title", "art", "playcount"],
                             limits=limits, returntype="", optparam=optparam)

    def files(self, vfspath, sort=None, limits=None):
        """gets all items in a kodi vfs path"""
        return self.get_json("Files.GetDirectory", returntype="", optparam=("directory", vfspath),
                             fields=FIELDS_FILES, sort=sort, limits=limits)

    def genres(self, media_type):
        """return all genres for the given media type (movie/tvshow/musicvideo)"""
        return self.get_json("VideoLibrary.GetGenres", fields=["thumbnail", "title"],
                             returntype="genres", optparam=("type", media_type))

    def song(self, db_id):
        """get songdetails from kodi db"""
        return self.get_json("AudioLibrary.GetSongDetails", returntype="songdetails",
                             fields=FIELDS_SONGS, optparam=("songid", try_parse_int(db_id)))

    def songs(self, sort=None, filters=None, limits=None, filtertype=None):
        """get songs from kodi db"""
        return self.get_json("AudioLibrary.GetSongs", sort=sort, filters=filters,
                             fields=FIELDS_SONGS, limits=limits, returntype="songs", filtertype=filtertype)

    def album(self, db_id):
        """get albumdetails from kodi db"""
        album = self.get_json("AudioLibrary.GetAlbumDetails", returntype="albumdetails",
                              fields=FIELDS_ALBUMS, optparam=("albumid", try_parse_int(db_id)))
        # override type as the kodi json api is returning the album type instead of mediatype
        album["type"] = "album"
        return album

    def albums(self, sort=None, filters=None, limits=None, filtertype=None):
        """get albums from kodi db"""
        albums = self.get_json("AudioLibrary.GetAlbums", sort=sort, filters=filters,
                               fields=FIELDS_ALBUMS, limits=limits, returntype="albums", filtertype=filtertype)
        # override type as the kodi json api is returning the album type instead of mediatype
        for album in albums:
            album["type"] = "album"
        return albums

    def artist(self, db_id):
        """get artistdetails from kodi db"""
        return self.get_json("AudioLibrary.GetArtistDetails", returntype="artistdetails",
                             fields=FIELDS_ARTISTS, optparam=("artistid", try_parse_int(db_id)))

    def artists(self, sort=None, filters=None, limits=None, filtertype=None):
        """get artists from kodi db"""
        return self.get_json("AudioLibrary.GetArtists", sort=sort, filters=filters,
                             fields=FIELDS_ARTISTS, limits=limits, returntype="artists", filtertype=filtertype)

    def recording(self, db_id):
        """get pvr recording from kodi db"""
        return self.get_json("PVR.GetRecordingDetails", returntype="recordingdetails",
                             fields=FIELDS_RECORDINGS, optparam=("recordingid", try_parse_int(db_id)))

    def recordings(self, limits=None):
        """get pvr recordings from kodi db"""
        return self.get_json("PVR.GetRecordings", fields=FIELDS_RECORDINGS, limits=limits, returntype="recordings")

    def channel(self, db_id):
        """get pvr channel from kodi db"""
        return self.get_json("PVR.GetChannelDetails", returntype="channeldetails",
                             fields=FIELDS_CHANNELS, optparam=("channelid", try_parse_int(db_id)))

    def channels(self, limits=None, channelgroupid="alltv"):
        """get pvr channels from kodi db"""
        return self.get_json("PVR.GetChannels", fields=FIELDS_CHANNELS, limits=limits,
                             returntype="channels", optparam=("channelgroupid", channelgroupid))

    def channelgroups(self, limits=None, channeltype="tv"):
        """get pvr channelgroups from kodi db"""
        return self.get_json("PVR.GetChannelGroups", fields=[], limits=limits,
                             returntype="channelgroups", optparam=("channeltype", channeltype))

    def timers(self, limits=None):
        """get pvr recordings from kodi db"""
        fields = ["title", "endtime", "starttime", "channelid", "summary", "file"]
        return self.get_json("PVR.GetTimers", fields=fields, limits=limits, returntype="timers")

    def favourites(self):
        """get kodi favourites"""
        items = self.get_favourites_from_file()
        if not items:
            fields = ["path", "thumbnail", "window", "windowparameter"]
            optparams = ("type", None)
            items = self.get_json("Favourites.GetFavourites", fields=fields, optparam=optparams)
        return items

    def castmedia(self, actorname):
        """helper to display all media (movies/shows) for a specific actor"""
        # use db counts as simple checksum
        filters = [{"operator": "contains", "field": "actor", "value": actorname}]
        all_items = self.movies(filters=filters)
        for item in self.tvshows(filters=filters):
            item["file"] = "videodb://tvshows/titles/%s" % item["tvshowid"]
            item["isFolder"] = True
            all_items.append(item)
        return all_items

    def actors(self):
        """return all actors"""
        all_items = []
        all_actors = []
        result = self.files("videodb://movies/actors")
        result += self.files("videodb://tvshows/actors")
        for item in result:
            if not item["label"] in all_actors:
                all_actors.append(item["label"])
                item["type"] = "actor"
                item["isFolder"] = True
                if not item["art"].get("thumb"):
                    item["art"]["thumb"] = "DefaultActor.png"
                all_items.append(item)
        return sorted(all_items, key=itemgetter("label"))

    @staticmethod
    def set_json(jsonmethod, params):
        """method to set info in the kodi json api"""
        kodi_json = {}
        kodi_json["jsonrpc"] = "2.0"
        kodi_json["method"] = jsonmethod
        kodi_json["params"] = params
        kodi_json["id"] = 1
        json_response = xbmc.executeJSONRPC(try_encode(json.dumps(kodi_json)))
        if sys.version_info.major == 3:
            return json.loads(json_response)
        else:
            return json.loads(json_response.decode('utf-8', 'replace'))

    @staticmethod
    def get_json(jsonmethod, sort=None, filters=None, fields=None, limits=None,
                 returntype=None, optparam=None, filtertype=None):
        """method to get details from the kodi json api"""
        kodi_json = {}
        kodi_json["jsonrpc"] = "2.0"
        kodi_json["method"] = jsonmethod
        kodi_json["params"] = {}
        if optparam:
            if isinstance(optparam, list):
                for param in optparam:
                    kodi_json["params"][param[0]] = param[1]
            else:
                kodi_json["params"][optparam[0]] = optparam[1]
        kodi_json["id"] = 1
        if sort:
            kodi_json["params"]["sort"] = sort
        if filters:
            if not filtertype:
                filtertype = "and"
            if len(filters) > 1:
                kodi_json["params"]["filter"] = {filtertype: filters}
            else:
                kodi_json["params"]["filter"] = filters[0]
        if fields:
            kodi_json["params"]["properties"] = fields
        if limits:
            kodi_json["params"]["limits"] = {"start": limits[0], "end": limits[1]}
        json_response = xbmc.executeJSONRPC(try_encode(json.dumps(kodi_json)))
        if sys.version_info.major == 3:
            json_object = json.loads(json_response)
        else:
            json_object = json.loads(json_response.decode('utf-8', 'replace'))
        # set the default returntype to prevent errors
        if "details" in jsonmethod.lower():
            result = {}
        else:
            result = []
        if 'result' in json_object:
            if returntype and returntype in json_object['result']:
                # returntype specified, return immediately
                result = json_object['result'][returntype]
            else:
                # no returntype specified, we'll have to look for it
                if sys.version_info.major == 3:
                    for key, value in json_object['result'].items():
                        if not key == "limits" and (isinstance(value, list) or isinstance(value, dict)):
                            result = value
                else:
                    for key, value in json_object['result'].iteritems():
                        if not key == "limits" and (isinstance(value, list) or isinstance(value, dict)):
                            result = value
        else:
            log_msg(json_response)
            log_msg(kodi_json)
        return result

    @staticmethod
    def get_favourites_from_file():
        """json method for favourites doesn't return all items (such as android apps) so retrieve them from file"""
        allfavourites = []
        try:
            from xml.dom.minidom import parse
            if sys.version_info.major == 3:
                favourites_path = xbmcvfs.translatePath('special://profile/favourites.xml')
            else:
                favourites_path = xbmc.translatePath('special://profile/favourites.xml').decode("utf-8")
            if xbmcvfs.exists(favourites_path):
                doc = parse(favourites_path)
                result = doc.documentElement.getElementsByTagName('favourite')
                for fav in result:
                    action = fav.childNodes[0].nodeValue
                    action = action.replace('"', '')
                    label = fav.attributes['name'].nodeValue
                    try:
                        thumb = fav.attributes['thumb'].nodeValue
                    except Exception:
                        thumb = ""
                    window = ""
                    windowparameter = ""
                    action_type = "unknown"
                    if action.startswith("StartAndroidActivity"):
                        action_type = "androidapp"
                    elif action.startswith("ActivateWindow"):
                        action_type = "window"
                        actionparts = action.replace("ActivateWindow(", "").replace(",return)", "").split(",")
                        window = actionparts[0]
                        if len(actionparts) > 1:
                            windowparameter = actionparts[1]
                    elif action.startswith("PlayMedia"):
                        action_type = "media"
                        action = action.replace("PlayMedia(", "")[:-1]
                    allfavourites.append({"label": label, "path": action, "thumbnail": thumb, "window": window,
                                          "windowparameter": windowparameter, "type": action_type})
        except Exception as exc:
            log_exception(__name__, exc)
        return allfavourites

    @staticmethod
    def create_listitem(item, as_tuple=True, offscreen=True):
        """helper to create a kodi listitem from kodi compatible dict with mediainfo"""
        try:
            if KODI_VERSION > 17:
                liz = xbmcgui.ListItem(
                    label=item.get("label", ""),
                    label2=item.get("label2", ""),
                    path=item['file'],
                    offscreen=offscreen)
            else:
                liz = xbmcgui.ListItem(
                    label=item.get("label", ""),
                    label2=item.get("label2", ""),
                    path=item['file'])

            # only set isPlayable prop if really needed
            if item.get("isFolder", False):
                liz.setProperty('IsPlayable', 'false')
            elif "plugin://script.skin.helper" not in item['file']:
                liz.setProperty('IsPlayable', 'true')

            nodetype = "Video"
            if item["type"] in ["song", "album", "artist"]:
                nodetype = "Music"

            # extra properties
            if sys.version_info.major == 3:
                for key, value in item["extraproperties"].items():
                    liz.setProperty(key, value)
            else:
                for key, value in item["extraproperties"].iteritems():
                    liz.setProperty(key, value)

            # video infolabels
            if nodetype == "Video":
                infolabels = {
                    "title": item.get("title"),
                    "size": item.get("size"),
                    "genre": item.get("genre"),
                    "year": item.get("year"),
                    "top250": item.get("top250"),
                    "tracknumber": item.get("tracknumber"),
                    "rating": item.get("rating"),
                    "playcount": item.get("playcount"),
                    "overlay": item.get("overlay"),
                    "cast": item.get("cast"),
                    "castandrole": item.get("castandrole"),
                    "director": item.get("director"),
                    "mpaa": item.get("mpaa"),
                    "plot": item.get("plot"),
                    "plotoutline": item.get("plotoutline"),
                    "originaltitle": item.get("originaltitle"),
                    "sorttitle": item.get("sorttitle"),
                    "duration": item.get("duration"),
                    "studio": item.get("studio"),
                    "tagline": item.get("tagline"),
                    "writer": item.get("writer"),
                    "tvshowtitle": item.get("tvshowtitle"),
                    "premiered": item.get("premiered"),
                    "status": item.get("status"),
                    "code": item.get("imdbnumber"),
                    "imdbnumber": item.get("imdbnumber"),
                    "aired": item.get("aired"),
                    "credits": item.get("credits"),
                    "album": item.get("album"),
                    "artist": item.get("artist"),
                    "votes": item.get("votes"),
                    "trailer": item.get("trailer")
                }
                #ERROR: NEWADDON Unknown Video Info Key "progress" in Kodi 19 ?!
                if KODI_VERSION < 18:
                    infolabels["progress"] = item.get('progresspercentage')
                if item["type"] == "episode":
                    infolabels["season"] = item["season"]
                    infolabels["episode"] = item["episode"]

                # streamdetails
                if item.get("streamdetails"):
                    liz.addStreamInfo("video", item["streamdetails"].get("video", {}))
                    liz.addStreamInfo("audio", item["streamdetails"].get("audio", {}))
                    liz.addStreamInfo("subtitle", item["streamdetails"].get("subtitle", {}))

                if "dateadded" in item:
                    infolabels["dateadded"] = item["dateadded"]
                if "date" in item:
                    infolabels["date"] = item["date"]

            # music infolabels
            else:
                infolabels = {
                    "title": item.get("title"),
                    "size": item.get("size"),
                    "genre": item.get("genre"),
                    "year": item.get("year"),
                    "tracknumber": item.get("track"),
                    "album": item.get("album"),
                    "artist": " / ".join(item.get('artist')),
                    "rating": str(item.get("rating", 0)),
                    "lyrics": item.get("lyrics"),
                    "playcount": item.get("playcount")
                }
                if "date" in item:
                    infolabels["date"] = item["date"]
                if "duration" in item:
                    infolabels["duration"] = item["duration"]
                if "lastplayed" in item:
                    infolabels["lastplayed"] = item["lastplayed"]

            # setting the dbtype and dbid is supported from kodi krypton and up
            if KODI_VERSION > 16 and item["type"] not in ["recording", "channel", "favourite", "genre", "categorie"]:
                infolabels["mediatype"] = item["type"]
                # setting the dbid on music items is not supported ?
                if nodetype == "Video" and "DBID" in item["extraproperties"]:
                    infolabels["dbid"] = item["extraproperties"]["DBID"]

            if "lastplayed" in item:
                infolabels["lastplayed"] = item["lastplayed"]

            # assign the infolabels
            liz.setInfo(type=nodetype, infoLabels=infolabels)

            # artwork
            liz.setArt(item.get("art", {}))
            if KODI_VERSION > 17:
                if "icon" in item:
                    liz.setArt({"icon":item['icon']})
                if "thumbnail" in item:
                    liz.setArt({"thumb":item['thumbnail']})
            else:
                if "icon" in item:
                    liz.setIconImage(item['icon'])
                if "thumbnail" in item:
                    liz.setThumbnailImage(item['thumbnail'])

            # contextmenu
            if item["type"] in ["episode", "season"] and "season" in item and "tvshowid" in item:
                # add series and season level to widgets
                if "contextmenu" not in item:
                    item["contextmenu"] = []
                item["contextmenu"] += [
                    (xbmc.getLocalizedString(20364), "ActivateWindow(Video,videodb://tvshows/titles/%s/,return)"
                        % (item["tvshowid"])),
                    (xbmc.getLocalizedString(20373), "ActivateWindow(Video,videodb://tvshows/titles/%s/%s/,return)"
                        % (item["tvshowid"], item["season"]))]
            if "contextmenu" in item:
                liz.addContextMenuItems(item["contextmenu"])

            if as_tuple:
                return item["file"], liz, item.get("isFolder", False)
            else:
                return liz
        except Exception as exc:
            log_exception(__name__, exc)
            log_msg(item)
            return None

    @staticmethod
    def prepare_listitem(item):
        """helper to convert kodi output from json api to compatible format for listitems"""
        try:
            # fix values returned from json to be used as listitem values
            properties = item.get("extraproperties", {})

            # set type
            for idvar in [
                ('episode', 'DefaultTVShows.png'),
                ('tvshow', 'DefaultTVShows.png'),
                ('movie', 'DefaultMovies.png'),
                ('song', 'DefaultAudio.png'),
                ('album', 'DefaultAudio.png'),
                ('artist', 'DefaultArtist.png'),
                ('musicvideo', 'DefaultMusicVideos.png'),
                ('recording', 'DefaultTVShows.png'),
                    ('channel', 'DefaultAddonPVRClient.png')]:
                dbid = item.get(idvar[0] + "id")
                if dbid:
                    properties["DBID"] = str(dbid)
                    if not item.get("type"):
                        item["type"] = idvar[0]
                    if not item.get("icon"):
                        item["icon"] = idvar[1]
                    break

            # general properties
            if "genre" in item and isinstance(item['genre'], list):
                item["genre"] = " / ".join(item['genre'])
            if "studio" in item and isinstance(item['studio'], list):
                item["studio"] = " / ".join(item['studio'])
            if "writer" in item and isinstance(item['writer'], list):
                item["writer"] = " / ".join(item['writer'])
            if 'director' in item and isinstance(item['director'], list):
                item["director"] = " / ".join(item['director'])
            if 'artist' in item and not isinstance(item['artist'], list):
                item["artist"] = [item['artist']]
            if 'artist' not in item:
                item["artist"] = []
            if item['type'] == "album" and 'album' not in item and 'label' in item:
                item['album'] = item['label']
            if "duration" not in item and "runtime" in item:
                if (item["runtime"] / 60) > 300:
                    item["duration"] = item["runtime"] / 60
                else:
                    item["duration"] = item["runtime"]
            if "plot" not in item and "comment" in item:
                item["plot"] = item["comment"]
            if "tvshowtitle" not in item and "showtitle" in item:
                item["tvshowtitle"] = item["showtitle"]
            if "premiered" not in item and "firstaired" in item:
                item["premiered"] = item["firstaired"]
            if "firstaired" in item and "aired" not in item:
                item["aired"] = item["firstaired"]
            if "imdbnumber" not in properties and "imdbnumber" in item:
                properties["imdbnumber"] = item["imdbnumber"]
            if "imdbnumber" not in properties and "uniqueid" in item:
                for value in item["uniqueid"].values():
                    if value.startswith("tt"):
                        properties["imdbnumber"] = value

            properties["dbtype"] = item["type"]
            properties["DBTYPE"] = item["type"]
            properties["type"] = item["type"]
            properties["path"] = item.get("file")

            # cast
            list_cast = []
            list_castandrole = []
            item["cast_org"] = item.get("cast", [])
            if "cast" in item and isinstance(item["cast"], list):
                for castmember in item["cast"]:
                    if isinstance(castmember, dict):
                        list_cast.append(castmember.get("name", ""))
                        list_castandrole.append((castmember["name"], castmember["role"]))
                    else:
                        list_cast.append(castmember)
                        list_castandrole.append((castmember, ""))

            item["cast"] = list_cast
            item["castandrole"] = list_castandrole

            if "season" in item and "episode" in item:
                properties["episodeno"] = "s%se%s" % (item.get("season"), item.get("episode"))
            if "resume" in item:
                properties["resumetime"] = str(item['resume']['position'])
                properties["totaltime"] = str(item['resume']['total'])
                properties['StartOffset'] = str(item['resume']['position'])

            # streamdetails
            if "streamdetails" in item:
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
                        properties["VideoResolution"] = resolution
                    if stream.get("codec", ""):
                        properties["VideoCodec"] = str(stream["codec"])
                    if stream.get("aspect", ""):
                        properties["VideoAspect"] = str(round(stream["aspect"], 2))
                    item["streamdetails"]["video"] = stream

                # grab details of first audio stream
                if len(audiostreams) > 0:
                    stream = audiostreams[0]
                    properties["AudioCodec"] = stream.get('codec', '')
                    properties["AudioChannels"] = str(stream.get('channels', ''))
                    properties["AudioLanguage"] = stream.get('language', '')
                    item["streamdetails"]["audio"] = stream

                # grab details of first subtitle
                if len(subtitles) > 0:
                    properties["SubtitleLanguage"] = subtitles[0].get('language', '')
                    item["streamdetails"]["subtitle"] = subtitles[0]
            else:
                item["streamdetails"] = {}
                item["streamdetails"]["video"] = {'duration': item.get('duration', 0)}

            # additional music properties
            if 'album_description' in item:
                properties["Album_Description"] = item.get('album_description')

            # pvr properties
            if "starttime" in item:
                # convert utc time to local time
                item["starttime"] = localdate_from_utc_string(item["starttime"])
                item["endtime"] = localdate_from_utc_string(item["endtime"])
                # set some localized versions of the time and date as additional properties
                startdate, starttime = localized_date_time(item['starttime'])
                enddate, endtime = localized_date_time(item['endtime'])
                properties["StartTime"] = starttime
                properties["StartDate"] = startdate
                properties["EndTime"] = endtime
                properties["EndDate"] = enddate
                properties["Date"] = "%s %s-%s" % (startdate, starttime, endtime)
                properties["StartDateTime"] = "%s %s" % (startdate, starttime)
                properties["EndDateTime"] = "%s %s" % (enddate, endtime)
                # set date to startdate
                item["date"] = arrow.get(item["starttime"]).format("DD.MM.YYYY")
            if "channellogo" in item:
                properties["channellogo"] = item["channellogo"]
                properties["channelicon"] = item["channellogo"]
            if "episodename" in item:
                properties["episodename"] = item["episodename"]
            if "channel" in item:
                properties["channel"] = item["channel"]
                properties["channelname"] = item["channel"]
                item["label2"] = item["title"]

            # artwork
            art = item.get("art", {})
            if item["type"] in ["episode", "season"]:
                if not art.get("fanart") and art.get("season.fanart"):
                    art["fanart"] = art["season.fanart"]
                if not art.get("poster") and art.get("season.poster"):
                    art["poster"] = art["season.poster"]
                if not art.get("landscape") and art.get("season.landscape"):
                    art["poster"] = art["season.landscape"]
                if not art.get("fanart") and art.get("tvshow.fanart"):
                    art["fanart"] = art.get("tvshow.fanart")
                if not art.get("poster") and art.get("tvshow.poster"):
                    art["poster"] = art.get("tvshow.poster")
                if not art.get("clearlogo") and art.get("tvshow.clearlogo"):
                    art["clearlogo"] = art.get("tvshow.clearlogo")
                if not art.get("banner") and art.get("tvshow.banner"):
                    art["banner"] = art.get("tvshow.banner")
                if not art.get("landscape") and art.get("tvshow.landscape"):
                    art["landscape"] = art.get("tvshow.landscape")
            if not art.get("fanart") and item.get('fanart'):
                art["fanart"] = item.get('fanart')
            if not art.get("thumb") and item.get('thumbnail'):
                art["thumb"] = get_clean_image(item.get('thumbnail'))
            if not art.get("thumb") and art.get('poster'):
                art["thumb"] = get_clean_image(art.get('poster'))
            if not art.get("thumb") and item.get('icon'):
                art["thumb"] = get_clean_image(item.get('icon'))
            if not item.get("thumbnail") and art.get('thumb'):
                item["thumbnail"] = art["thumb"]

            # clean art
            if sys.version_info.major == 3:
                for key, value in art.items():
                    if not isinstance(value, str):
                        art[key] = ""
                    elif value:
                        art[key] = get_clean_image(value)
            else:
                if sys.version_info.major == 3:
                    for key, value in art.items():
                        if not isinstance(value, str):
                            art[key] = ""
                        elif value:
                            art[key] = get_clean_image(value)
                else:
                    for key, value in art.iteritems():
                        if not isinstance(value, (str, unicode)):
                            art[key] = ""
                        elif value:
                            art[key] = get_clean_image(value)
            item["art"] = art

            item["extraproperties"] = properties

            if "file" not in item:
                log_msg("Item is missing file path ! --> %s" % item["label"], xbmc.LOGWARNING)
                item["file"] = ""

            # return the result
            return item

        except Exception as exc:
            log_exception(__name__, exc)
            log_msg(item)
            return None

    @staticmethod
    def tvshow_watchedcounts(tvshow):
        """append watched counts to tvshow details"""
        tvshow["extraproperties"] = {"totalseasons": str(tvshow["season"]),
                                     "totalepisodes": str(tvshow["episode"]),
                                     "watchedepisodes": str(tvshow["watchedepisodes"]),
                                     "unwatchedepisodes": str(tvshow["episode"] - tvshow["watchedepisodes"])
                                     }
        return tvshow
