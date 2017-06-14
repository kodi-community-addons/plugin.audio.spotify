#!/usr/bin/python
# -*- coding: utf-8 -*-

import SimpleHTTPServer
import BaseHTTPServer
import SocketServer
import httplib
import threading
from utils import log_msg, log_exception, create_wave_header, kill_librespot, PROXY_PORT, parse_spotify_track
import xbmc
import xbmcvfs
import urlparse
import urllib
import socket

quit_event = threading.Event()


class WebService(threading.Thread):
    '''Main webservice class which holds the BaseHTTPServer instance'''
    exit = False
    server = None

    def __init__(self, *args, **kwargs):
        self.sp = kwargs.get("sp")
        self.kodiplayer = kwargs.get("kodiplayer")
        self.librespot = kwargs.get("librespot")
        self.connect_daemon = kwargs.get("connect_daemon")
        threading.Thread.__init__(self, *args)

    @staticmethod
    def stop_server():
        '''send stop command to webserver'''
        try:
            conn = httplib.HTTPConnection("127.0.0.1:%d" % PROXY_PORT)
            conn.request("QUIT", "/")
            conn.getresponse()
        except:
            pass

    def stop(self):
        '''called when the thread needs to stop'''
        log_msg("Audio proxy - stop called")
        self.server.exit = True
        self.stop_server()
        quit_event.wait()
        self.server.shutdown()
        self.join(0.1)
        log_msg("Audio proxy - stopped")

    def run(self):
        '''called to start our webservice'''
        log_msg("Audio proxy started on port %s" % PROXY_PORT, xbmc.LOGNOTICE)
        try:
            self.server = StoppableHttpServer(('127.0.0.1', PROXY_PORT), StoppableHttpRequestHandler)
            self.server.sp = self.sp
            self.server.kodiplayer = self.kodiplayer
            self.server.librespot = self.librespot
            self.server.connect_daemon = self.connect_daemon
            self.server.exit = False
            self.server.cur_singletrack = None
            self.server.serve_forever()
        except Exception as exc:
            log_exception(__name__, exc)


class StoppableHttpRequestHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    '''http request handler with QUIT stopping the server'''
    raw_requestline = ""
    librespot_bin = None

    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.handle(self)
        except Exception as exc:
            #log_exception(__name__, exc)
            pass
        except SystemExit:
            pass

    def finish(self, *args, **kw):
        if self.librespot_bin:
            self.librespot_bin.terminate()
        try:
            if not self.wfile.closed:
                self.wfile.flush()
                self.wfile.close()
        except Exception as exc:
            #log_exception(__name__, exc)
            pass
        except SystemExit:
            pass
        self.rfile.close()

    def do_QUIT(self):
        '''send 200 OK response, and set server.exit to True'''
        quit_event.set()
        self.server.exit = True
        self.send_response(200)
        self.end_headers()

    def log_message(self, logformat, *args):
        ''' log message to kodi log'''
        log_msg("Webservice --> [%s] %s\n" % (self.log_date_time_string(), logformat % args), xbmc.LOGDEBUG)

    def send_headers(self, filesize=None):
        self.send_response(200)
        if "playercmd" in self.path or "callback" in self.path:
            self.send_header("Content-type", "text/html")
        else:
            self.send_header('Content-type', 'audio/wave')
            self.send_header('Connection', 'Close')
            self.send_header('Accept-Ranges', 'None')
            if filesize:
                self.send_header('Content-Length', '%s' %filesize)
        self.end_headers()

    def do_GET(self):
        '''send headers and reponse'''
        if "callback" in self.path:
            self.auth_callback()
        elif "playercmd" in self.path:
            self.player_control()
        elif "connect" in self.path:
            self.connect_track()
        elif "nexttrack" in self.path:
            self.connect_track(10)
            self.server.sp.next_track()
        elif "track" in self.path:
            self.single_track()
        return

    def do_HEAD():
        self.send_header('Content-type', 'audio/wave')
        self.send_header('Connection', 'Close')
        self.send_header('Accept-Ranges', 'None')
    
    def single_track(self):
        track_id = self.path.split("/")[-1]
        log_msg("Playback requested for track %s" % track_id)
        self.server.cur_singletrack = track_id
        track_info = self.server.sp.track(track_id)
        duration = track_info["duration_ms"] / 1000
        wave_header, filesize = create_wave_header(duration)
        self.wfile._sock.settimeout(duration)
        self.send_headers(filesize)
        self.wfile.write(wave_header)
        args = ["-n", "temp", "--single-track", track_id, "--backend", "pipe"]
        self.librespot_bin = self.server.librespot.run_librespot(args)
        if self.server.librespot.buffer_track:
            # send entire trackdata at once
            stdout, stderr = self.librespot_bin.communicate()
            self.wfile.write(stdout)
        else:
            # (semi)chunked transfer of data
            bufsize = filesize / 5
            log_msg("start chunked transfer of track")
            while True:
                chunk = self.librespot_bin.stdout.read(bufsize)
                self.wfile.write(chunk)
                if len(chunk) < bufsize:
                    log_msg("end of stream")
                    break

    def connect_track(self, duration=0):
        # we're asked to play a track by spotify connect
        # the connect player is playing audio itself so we just stream silence to fake playback to kodi
        if not duration:
            duration = int(self.path.split("/")[-1])
        wave_header, filesize = create_wave_header(duration)
        self.send_headers(filesize)
        self.wfile.write(wave_header)
        # stream silence untill the next track is received
        self.wfile.write('\0' * filesize)
        
    def player_control(self):
        '''special entrypoint which can be used to control the kodiplayer by the librespot daemon'''
        self.send_headers()
        self.wfile.write("OK")
        if "start" in self.path or "change" in self.path:
            # connect wants us to play a track
            if "start" in self.path and self.server.kodiplayer.connect_playing:
                log_msg("Resume playback requested by Spotify Connect", xbmc.LOGNOTICE)
                self.server.kodiplayer.play()
                return
            elif "start" in self.path:
                self.server.kodiplayer.stop()
                log_msg("Start playback requested by Spotify Connect", xbmc.LOGNOTICE)
                xbmc.sleep(500)
            else:
                log_msg("Next track requested by Spotify Connect", xbmc.LOGNOTICE)
            self.server.kodiplayer.playlist.clear()
            trackdetails = self.server.sp.track(self.server.connect_daemon.cur_track)
            url, li = parse_spotify_track(trackdetails, is_connect=True)
            self.server.kodiplayer.playlist.add(url, li)
            self.server.kodiplayer.play()
        elif "stop" in self.path:
            log_msg("Stop playback requested by Spotify Connect", xbmc.LOGNOTICE)
            if not xbmc.getCondVisibility("Player.Paused"):
                self.server.kodiplayer.stop()
        return

    def auth_callback(self):
        '''callback for spotify authentication request'''
        log_msg("auth_callback called")
        self.send_headers()
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Authentication succesfull</title></head>")
        self.wfile.write("<p>You can now close this browser window.</p>")
        self.wfile.write("</body></html>")
        self.wfile.close()
        xbmc.executebuiltin("SetProperty(spotify-token-info,%s,Home)" % self.path)
        log_msg("authkey sent")
        return


class StoppableHttpServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""
    pass
