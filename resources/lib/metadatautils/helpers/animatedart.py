#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Retrieve animated artwork for kodi movies"""

import os, sys
if sys.version_info.major == 3:
    from .utils import get_json, DialogSelect, log_msg, ADDON_ID
else:
    from utils import get_json, DialogSelect, log_msg, ADDON_ID
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
from simplecache import use_cache
from datetime import timedelta


class AnimatedArt(object):
    """get animated artwork"""
    ignore_cache = False

    def __init__(self, simplecache=None, kodidb=None):
        """Initialize - optionaly provide SimpleCache and KodiDb object"""

        if not kodidb:
            if sys.version_info.major == 3:
                from .kodidb import KodiDb
            else:
                from kodidb import KodiDb
            self.kodidb = KodiDb()
        else:
            self.kodidb = kodidb

        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache

    @use_cache(14)
    def get_animated_artwork(self, imdb_id, manual_select=False, ignore_cache=False):
        """returns all available animated art for the given imdbid/tmdbid"""
        # prefer local result
        kodi_movie = self.kodidb.movie_by_imdbid(imdb_id)
        if not manual_select and kodi_movie and kodi_movie["art"].get("animatedposter"):
            result = {
                "animatedposter": kodi_movie["art"].get("animatedposter"),
                "animatedfanart": kodi_movie["art"].get("animatedfanart")
            }
        else:
            result = {
                "animatedposter": self.poster(imdb_id, manual_select),
                "animatedfanart": self.fanart(imdb_id, manual_select),
                "imdb_id": imdb_id
            }
            self.write_kodidb(result)
        log_msg("get_animated_artwork for imdbid: %s - result: %s" % (imdb_id, result))
        return result

    def poster(self, imdb_id, manual_select=False):
        """return preferred animated poster, optionally show selectdialog for manual selection"""
        img = self.select_art(self.posters(imdb_id), manual_select, "poster")
        return self.process_image(img, "poster", imdb_id)

    def fanart(self, imdb_id, manual_select=False):
        """return preferred animated fanart, optionally show selectdialog for manual selection"""
        img = self.select_art(self.fanarts(imdb_id), manual_select, "fanart")
        return self.process_image(img, "fanart", imdb_id)

    def posters(self, imdb_id):
        """return all animated posters for the given imdb_id (imdbid can also be tmdbid)"""
        return self.get_art(imdb_id, "posters")

    def fanarts(self, imdb_id):
        """return animated fanarts for the given imdb_id (imdbid can also be tmdbid)"""
        return self.get_art(imdb_id, "fanarts")

    def get_art(self, imdb_id, art_type):
        """get the artwork"""
        art_db = self.get_animatedart_db()
        if art_db.get(imdb_id):
            return art_db[imdb_id][art_type]
        return []

    def get_animatedart_db(self):
        """get the full animated art database as dict with imdbid and tmdbid as key
        uses 7 day cache to prevent overloading the server"""
        # get all animated posters from the online json file
        cache = self.cache.get("animatedartdb")
        if cache:
            return cache
        art_db = {}
        data = get_json('http://www.consiliumb.com/animatedgifs/movies.json', None)
        base_url = data.get("baseURL", "")
        if data and data.get('movies'):
            for item in data['movies']:
                for db_id in ["imdbid", "tmdbid"]:
                    key = item[db_id]
                    art_db[key] = {"posters": [], "fanarts": []}
                    for entry in item['entries']:
                        entry_new = {
                            "contributedby": entry["contributedBy"],
                            "dateadded": entry["dateAdded"],
                            "language": entry["language"],
                            "source": entry["source"],
                            "image": "%s/%s" % (base_url, entry["image"].replace(".gif", "_original.gif")),
                            "thumb": "%s/%s" % (base_url, entry["image"])}
                        if entry['type'] == 'poster':
                            art_db[key]["posters"].append(entry_new)
                        elif entry['type'] == 'background':
                            art_db[key]["fanarts"].append(entry_new)
            self.cache.set("animatedartdb", art_db, expiration=timedelta(days=7))
        return art_db

    @staticmethod
    def select_art(items, manual_select=False, art_type=""):
        """select the preferred image from the list"""
        image = None
        if manual_select:
            # show selectdialog to manually select the item
            results_list = []
            # add none and browse entries
            listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(231))
            listitem.setArt({'icon': "DefaultAddonNone.png"})
            results_list.append(listitem)
            listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(1030))
            listitem.setArt({'icon': "DefaultFolder.png"})
            results_list.append(listitem)
            for item in items:
                labels = [item["contributedby"], item["dateadded"], item["language"], item["source"]]
                label = " / ".join(labels)
                listitem = xbmcgui.ListItem(label=label)
                listitem.setArt({'icon': item["thumb"]})
                results_list.append(listitem)
            if manual_select and results_list:
                dialog = DialogSelect("DialogSelect.xml", "", listing=results_list, window_title=art_type)
                dialog.doModal()
                selected_item = dialog.result
                del dialog
                if selected_item == 0:
                    image = ""
                if selected_item == 1:
                    # browse for image
                    dialog = xbmcgui.Dialog()
                    if sys.version_info.major == 3:
                        image = dialog.browse(2, xbmc.getLocalizedString(1030), 'files', mask='.gif')
                    else:
                        image = dialog.browse(2, xbmc.getLocalizedString(1030), 'files', mask='.gif').decode("utf-8")
                    del dialog
                elif selected_item > 1:
                    # user has selected an image from online results
                    image = items[selected_item - 2]["image"]
        elif items:
            # just grab the first item as best match
            image = items[0]["image"]
        return image

    @staticmethod
    def process_image(image_url, art_type, imdb_id):
        """animated gifs need to be stored locally, otherwise they won't work"""
        # make sure that our local path for the gif images exists
        addon = xbmcaddon.Addon(ADDON_ID)
        gifs_path = "%sanimatedgifs/" % addon.getAddonInfo('profile')
        del addon
        if not xbmcvfs.exists(gifs_path):
            xbmcvfs.mkdirs(gifs_path)
        # only process existing images
        if not image_url or not xbmcvfs.exists(image_url):
            return None
        # copy the image to our local path and return the new path as value
        local_filename = "%s%s_%s.gif" % (gifs_path, imdb_id, art_type)
        if xbmcvfs.exists(local_filename):
            xbmcvfs.delete(local_filename)
        # we don't use xbmcvfs.copy because we want to wait for the action to complete
        img = xbmcvfs.File(image_url)
        img_data = img.readBytes()
        img.close()
        img = xbmcvfs.File(local_filename, 'w')
        img.write(img_data)
        img.close()
        return local_filename

    def write_kodidb(self, artwork):
        """store the animated artwork in kodi database to access it with ListItem.Art(animatedartX)"""
        kodi_movie = self.kodidb.movie_by_imdbid(artwork["imdb_id"])
        if kodi_movie:
            params = {
                "movieid": kodi_movie["movieid"],
                "art": {"animatedfanart": artwork["animatedfanart"], "animatedposter": artwork["animatedposter"]}
            }
            self.kodidb.set_json('VideoLibrary.SetMovieDetails', params)
