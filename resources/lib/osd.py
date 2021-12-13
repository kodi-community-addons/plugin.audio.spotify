#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.spotify
    osd.py
    Special window to display an OSD for remote control of Connect player
'''

import threading
import _thread
import xbmc
import xbmcgui
from utils import log_msg, log_exception, get_track_rating
from metadatautils import MetadataUtils


class SpotifyOSD(xbmcgui.WindowXMLDialog):
    ''' Special OSD to control Spotify Connect player'''
    update_thread = None
    sp = None
    is_playing = True
    shuffle_state = False
    repeat_state = "off"

    def __init__(self, *args, **kwargs):
        self.metadatautils = MetadataUtils()
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        '''triggers on initialization of the dialog'''
        self.update_thread = SpotifyOSDUpdateThread()
        self.update_thread.set_dialog(self)
        self.update_thread.start()

    def onAction(self, action):
        '''triggers on kodi navigation events'''
        action_id = action.getId()
        if action_id in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close_dialog()
        elif action_id in (12, 68, 79, 229):
            self.toggle_playback()
        elif action_id in (184, 14, 97):
            self.sp.next_track()
        elif action_id in (185, 15, 98):
            self.sp.previous_track()

    def close_dialog(self):
        '''stop background thread and close the dialog'''
        self.update_thread.stop_running()
        try:
            self.sp.pause_playback()
        except:
            pass
        self.metadatautils.close()
        self.close()

    def onClick(self, control_id):
        '''Kodi builtin: triggers if window is clicked'''
        if control_id == 3201:
            self.sp.previous_track()
        elif control_id == 3203:
            self.toggle_playback()
        elif control_id == 3204:
            self.sp.next_track()
        elif control_id == 3206 and self.shuffle_state:
            self.sp.shuffle(False)
        elif control_id == 3206 and not self.shuffle_state:
            self.sp.shuffle(True)
        elif control_id == 3208 and self.repeat_state == "off":
            self.sp.repeat("track")
        elif control_id == 3208 and self.repeat_state == "track":
            self.sp.repeat("context")
        elif control_id == 3208 and self.repeat_state == "context":
            self.sp.repeat("off")

    def toggle_playback(self):
        '''toggle play/pause'''
        if self.is_playing:
            self.is_playing = False
            self.getControl(3202).setEnabled(False)
            try:
                self.sp.pause_playback()
            except Exception:
                pass
        else:
            self.is_playing = True
            self.getControl(3202).setEnabled(True)
            self.sp.start_playback()
    
class SpotifyOSDUpdateThread(threading.Thread):
    '''Background thread to complement our OSD dialog,
    fills the listing while UI keeps responsive'''
    active = True
    dialog = None
    search_string = ""

    def __init__(self, *args):
        log_msg("SpotifyOSDUpdateThread Init")
        threading.Thread.__init__(self, *args)

    def stop_running(self):
        '''stop thread end exit'''
        self.active = False

    def set_dialog(self, dialog):
        '''set the active dialog to perform actions'''
        self.dialog = dialog

    def run(self):
        '''Main run loop for the background thread'''
        last_title = ""
        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and self.active:
            cur_playback = self.get_curplayback()
            if cur_playback and cur_playback.get("item"):
                if cur_playback["shuffle_state"] != self.dialog.shuffle_state:
                    self.toggle_shuffle(cur_playback["shuffle_state"])
                if cur_playback["repeat_state"] != self.dialog.repeat_state:
                    self.set_repeat(cur_playback["repeat_state"])
                if cur_playback["is_playing"] != self.dialog.is_playing:
                    self.toggle_playstate(cur_playback["is_playing"])
                cur_title = cur_playback["item"]["uri"]
                if cur_title != last_title:
                    last_title = cur_title
                    trackdetails = cur_playback["item"]
                    self.update_info(trackdetails)
            monitor.waitForAbort(2)

        del monitor

    def get_curplayback(self):
        '''get current playback details - retry on error'''
        count = 5
        while count and self.active:
            try:
                cur_playback = self.dialog.sp.current_playback()
                return cur_playback
            except Exception as exc:
                if "token expired" in str(exc):
                    token = xbmc.getInfoLabel("Window(Home).Property(spotify-token)")
                    self.sp._auth = token
                else:
                    log_exception(__name__, exc)
            count -= 1
            xbmc.sleep(500)
        self.dialog.close_dialog()
        return None

    def toggle_playstate(self, value):
        '''toggle pause/play'''
        self.dialog.is_playing = value
        self.dialog.getControl(3202).setEnabled(value)

    def toggle_shuffle(self, value):
        '''toggle shuffle'''
        self.dialog.shuffle_state = value
        self.dialog.getControl(3205).setEnabled(value)

    def set_repeat(self, value):
        '''set repeat state'''
        self.dialog.repeat_state = value
        self.dialog.getControl(3207).setLabel(value)

    def update_info(self, track=None):
        '''scrape results for search query'''

        # set cover image
        thumb = ""
        if track.get("images"):
            thumb = track["images"][0]['url']
        elif track['album'].get("images"):
            thumb = track['album']["images"][0]['url']
        self.dialog.getControl(3110).setImage(thumb)

        # set track title
        lbl_control = self.dialog.getControl(3111)
        title = track["name"]
        lbl_control.setLabel(title)

        # set artist label
        lbl_control = self.dialog.getControl(3112)
        artist = " / ".join([artist["name"] for artist in track["artists"]])
        lbl_control.setLabel(artist)

        # set album label
        lbl_control = self.dialog.getControl(3113)
        album = track['album']["name"]
        lbl_control.setLabel(album)

        # set genre label
        lbl_control = self.dialog.getControl(3114)
        genre = " / ".join(track["album"].get("genres", []))
        lbl_control.setLabel(genre)

        # set rating label
        lbl_control = self.dialog.getControl(3115)
        rating = str(get_track_rating(track["popularity"]))
        lbl_control.setLabel(rating)

        # get additional artwork
        artwork = self.dialog.metadatautils.get_music_artwork(artist, album, title)
        fanart = artwork["art"].get("fanart", "special://home/addons/plugin.audio.spotify/fanart.jpg")
        self.dialog.getControl(3300).setImage(fanart)
        efa = artwork["art"].get("extrafanart", "")
        self.dialog.getControl(3301).setLabel(efa)
        clearlogo = artwork["art"].get("clearlogo", "")
        self.dialog.getControl(3303).setImage(clearlogo)
        banner = artwork["art"].get("banner", "")
        self.dialog.getControl(3304).setImage(banner)
        albumthumb = artwork["art"].get("albumthumb", "")
        self.dialog.getControl(3305).setImage(albumthumb)
        artistthumb = artwork["art"].get("artistthumb", "")
        self.dialog.getControl(3306).setImage(artistthumb)
        discart = artwork["art"].get("discart", "disc.png")
        self.dialog.getControl(3307).setImage(discart)
