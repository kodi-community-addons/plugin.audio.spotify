# -*- coding: utf8 -*-
from __future__ import print_function, unicode_literals
from utils import *
from spotify import link, track, image
import time
import math
import random
from taskutils.decorators import run_in_thread
from taskutils.threads import current_task
from spotify.utils.loaders import load_track
import re

class PlaylistManager:
    __server_port = None
    __user_agent = None
    __play_token = None
    __url_headers = None
    __playlist = None
    __a6df109_fix = None
    __server_ip = None
    __player = None
    __loop_task = None

    def __init__(self, server):
        self.__server_port = server.get_port()
        self.__play_token = server.get_user_token(self._get_user_agent())
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        self.__player = xbmc.Player()
        self.__a6df109_fix = 'a6df109' in xbmc.getInfoLabel(
            'System.BuildVersion')
        self.__server_ip = server.get_host()

    def _get_user_agent(self):
        if self.__user_agent is None:
            xbmc_build = xbmc.getInfoLabel("System.BuildVersion")
            self.__user_agent = 'Spotify/{0} (XBMC/{1})'.format(
                ADDON_VERSION, xbmc_build)

        return self.__user_agent

    # Unused
    def _get_play_token(self):
        return self.__play_token

    def _play_item(self, offset):
        self.__player.playselected(offset)

    def clear(self):
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        self.__playlist.clear()

    def _get_track_id(self, track):
        track_link = link.create_from_track(track)
        return track_link.as_string()[14:]

    def _get_url_headers(self):
        if self.__url_headers is None:
            str_agent = self._get_user_agent()
            str_token = self._get_play_token()
            header_dict = {
                'User-Agent': str_agent,
                'X-Spotify-Token': str_token
                }
            self.__url_headers = urlencode(header_dict)

        return self.__url_headers

    def get_track_url(self, track, list_index=None):
        track_id = self._get_track_id(track)
        headers = self._get_url_headers()
        url = ""
        if list_index is not None:
            args = (
                self.__server_ip, self.__server_port,
                track_id, list_index, headers
            )
            url = 'http://{0}:{1:d}/track/{2}.wav?idx={3:d}|{4}'.format(*args)
        else:
            args = (self.__server_ip, self.__server_port, track_id, headers)
            url = 'http://{0}:{1:d}/track/{2}.wav|{3}'.format(*args)
        return url

    def get_image_url(self, image_id):
        if image_id is not None:
            args = (self.__server_ip, self.__server_port, image_id)
            return 'http://{0}:{1:d}/image/{2}.jpg'.format(*args)
        else:
            return ''

    def _calculate_track_rating(self, track):
        popularity = track.popularity()
        if popularity == 0:
            return 0
        else:
            return int(math.ceil(popularity * 6 / 100.0)) - 1

    def _item_is_playable(self, session, track_obj):
        return track_obj.get_availability(session) == \
            track.TrackAvailability.Available

    def _get_track_images(self, track_obj, session):

        #If it's local, let's get the images from the autolinked one
        if track_obj.is_local(session):
            track_obj = track_obj.get_playable(session)

        return(
            self.get_image_url(track_obj.album().cover()),
            self.get_image_url(track_obj.album().cover(image.ImageSize.Large))
        )

    def create_track_info(self, track_obj, session, list_index=None):

        #Track is ok
        if track_obj.is_loaded() and track_obj.error() == 0:

            #Get track attributes
            album = track_obj.album().name()
            artist = ' / '.join([artist.name().decode("utf-8") for artist
                                in track_obj.artists()])
            normal_image, large_image = self._get_track_images(
                track_obj, session)
            track_url = self.get_track_url(track_obj, list_index)
            rating_points = str(self._calculate_track_rating(track_obj))

            item = xbmcgui.ListItem(
                track_obj.name(),
                path=track_url,
                iconImage=normal_image,
                thumbnailImage=large_image
            )
            info = {
                "title": track_obj.name(),
                "album": album,
                "artist": artist,
                "duration": track_obj.duration() / 1000,
                "tracknumber": track_obj.index(),
                "rating": rating_points,
            }
            item.setInfo("music", info)

            if list_index is not None:
                item.setProperty('ListIndex', str(list_index))

            if track_obj.is_starred(session):
                item.setProperty('IsStarred', 'true')
            else:
                item.setProperty('IsStarred', 'false')

            if self._item_is_playable(session, track_obj):
                item.setProperty('IsAvailable', 'true')
            else:
                item.setProperty('IsAvailable', 'false')

            #Rating points, again as a property for the custom stars
            item.setProperty('RatingPoints', rating_points)

            #Tell that analyzing the stream data is discouraged
            item.setProperty('do_not_analyze', 'true')

            return track_url, item

        #Track has errors
        else:
            return '', xbmcgui.ListItem()

    def stop(self, block=True):
        #Stop the stream and wait until it really got stopped
        #self.__player.stop()

        xbmc.executebuiltin('PlayerControl(stop)')

        while block and self.__player.isPlaying():
            time.sleep(.1)

    def _add_item(self, index, track, session):
        path, info = self.create_track_info(track, session, index)

        if self.__a6df109_fix:
            self.__playlist.add(path, info)
        else:
            self.__playlist.add(path, info, index)

    def is_playing(self, consider_pause=True):
        if consider_pause:
            return xbmc.getCondVisibility('Player.Playing | Player.Paused')
        else:
            return xbmc.getCondVisibility('Player.Playing')

    def get_shuffle_status(self):
        #Get it directly from a boolean tag (if possible)
        if self.is_playing() and len(self.__playlist) > 0:
            return xbmc.getCondVisibility('Playlist.IsRandom')
        else:
            return False


    @run_in_thread(max_concurrency=1)
    def _set_tracks(self, track_list, session, omit_offset):

        #Set the reference to the loop task
        self.__loop_task = current_task()

        #Clear playlist if no offset is given to omit
        if omit_offset is None:
            self.clear()

        #Iterate over the rest of the playlist
        for list_index, track in enumerate(track_list):

            #Check if we should continue
            self.__loop_task.check_status()

            #Don't add unplayable items to the playlist
            if self._item_is_playable(session, track):

                #Ignore the item at offset, which is already added
                if list_index != omit_offset:
                    self._add_item(list_index, track, session)

            #Deal with any potential dummy items
            if omit_offset is not None and list_index < omit_offset:
                self.__playlist.remove('dummy-{0:d}'.format(list_index))

        #Set paylist's shuffle status
        if self.get_shuffle_status():
            self.__playlist.shuffle()

        #Clear the reference to the task
        self.__loop_task = None

    def _cancel_loop(self):
        if self.__loop_task is not None:
            try:
                self.__loop_task.cancel()
            except:
                pass

    def set_tracks(self, track_list, session, omit_offset=None):
        self._cancel_loop()
        self._set_tracks(track_list, session, omit_offset)

    def play(self, track_list, session, offset=None):
        if len(track_list) > 0:

            #Cancel any possible set_tracks() loop
            self._cancel_loop()

            #Get shuffle status
            is_shuffle = self.get_shuffle_status()

            #Clear the old contents
            self.clear()

            #If we don't have an offset, get one
            if offset is None:
                if is_shuffle:
                    #TODO: Should loop for a playable item
                    offset = random.randint(0, len(track_list) - 1)
                else:
                    offset = 0

            #Check if the selected item is playable
            if not self._item_is_playable(session, track_list[offset]):
                d = xbmcgui.Dialog()
                d.ok('Spotify', 'The selected track is not playable')

            #Continue normally
            else:

                #Add some padding dummy items (to preserve playlist position)
                if offset > 0:
                    for index in range(offset):
                        tmpStr = 'dummy-{0:d}'.format(index)
                        self.__playlist.add(tmpStr, xbmcgui.ListItem(''))

                #Add the desired item and play it
                self._add_item(offset, track_list[offset], session)
                self._play_item(offset)

                #If there are items left...
                if len(track_list) > 1:
                    self.set_tracks(track_list, session, offset)

    def _get_track_from_url(self, sess_obj, url):

        #Get the clean track if from the url
        path = urlparse(url).path
        r = re.compile('^/track/(.+?)(?:\.wav)?$', re.IGNORECASE)
        mo = r.match(path)

        #If we succeed, create the object
        if mo is not None:

            #Try loading it as a spotify track
            link_obj = link.create_from_string("spotify:track:{0}".format(
                mo.group(1)))
            if link_obj is not None:
                return load_track(sess_obj, link_obj.as_track())

            #Try to parse as a local track
            tmpStr = "spotify:local:{0}".format(mo.group(1))
            link_obj = link.create_from_string(tmpStr)
            if link_obj is not None:

                #return the autolinked one, instead of the local track
                local_track = link_obj.as_track()
                return load_track(sess_obj, local_track.get_playable(sess_obj))

    def get_item(self, sess_obj, index):
        item = self.__playlist[index]
        return self._get_track_from_url(sess_obj, item.getfilename())

    def get_current_item(self, sess_obj):
        return self._get_track_from_url(
            sess_obj, xbmc.getInfoLabel('Player.Filenameandpath')
        )

    def get_next_item(self, sess_obj):
        next_index = self.__playlist.getposition() + 1
        if next_index < len(self.__playlist):
            return self.get_item(sess_obj, next_index)

    def __del__(self):
        #Cancel the set_tracks() loop at exit
        self.__cancel_set_tracks = True
