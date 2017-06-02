#!/usr/bin/python
# -*- coding: utf-8 -*-

import SimpleHTTPServer
import BaseHTTPServer
import SocketServer
import httplib
import threading
from utils import log_msg, log_exception, create_wave_header, kill_spotty, PROXY_PORT
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
        self.spotty = kwargs.get("spotty")
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
            self.server.spotty = self.spotty
            self.server.exit = False
            self.server.serve_forever()
        except Exception as exc:
            log_exception(__name__, exc)


class StoppableHttpRequestHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    '''http request handler with QUIT stopping the server'''
    raw_requestline = ""
    spotty_bin = None

    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.handle(self)
        except Exception as exc:
            log_exception(__name__, exc)
        except SystemExit:
            pass

    def finish(self, *args, **kw):
        if self.spotty_bin:
            self.spotty_bin.terminate()
        try:
            if not self.wfile.closed:
                self.wfile.flush()
                self.wfile.close()
        except:
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

    def do_HEAD(self):
        '''called on HEAD requests'''
        self.send_headers()

    def send_headers(self):
        self.send_response(200)
        if "playercmd" in self.path or "callback" in self.path:
            self.send_header("Content-type", "text/html")
        else:
            self.send_header('Content-type', 'audio/wave')
            self.send_header('Connection', 'Keep-Alive')
        self.end_headers()

    def do_GET(self):
        '''send headers and reponse'''
        self.send_headers()
        if "callback" in self.path:
            self.auth_callback()
        elif "loadtrack" in self.path:
            self.load_connect_track()
        elif "track" in self.path:
            self.single_track()
        elif "playercmd" in self.path:
            self.player_control()
        return

    def single_track(self):
        track_id = self.path.split("/")[-1]
        log_msg("Playback requested for track %s" % track_id)
        track_info = self.server.sp.track(track_id)
        duration = track_info["duration_ms"] / 1000
        wave_header, filesize = create_wave_header(duration)
        self.wfile.write(wave_header)
        self.wfile._sock.settimeout(duration)
        args = ["--single-track", track_id]
        self.spotty_bin = self.server.spotty.run_spotty(arguments=args)
        bytes_written = 0
        while bytes_written < filesize:
            line = self.spotty_bin.stdout.readline()
            if self.server.exit or not line:
                break
            bytes_written += len(line)
            self.wfile.write(line)

    def load_connect_track(self):
        # tell connect player to move to the next track
        self.server.sp.next_track()
        duration = 10
        self.wfile._sock.settimeout(duration)
        wave_header, filesize = create_wave_header(duration)
        self.wfile.write(wave_header)
        # stream silence untill the next track is received
        bytes_written = 0
        while bytes_written < filesize and not self.server.exit:
            bytes_written += 65536
            self.wfile.write('\0' * 65536)

    def player_control(self):
        if "start" in self.path or "change" in self.path:
            log_msg("Start playback requested by Spotify Connect", xbmc.LOGNOTICE)
            self.server.kodiplayer.update_playlist()
            self.wfile.write("OK")
        elif "stop" in self.path:
            log_msg("Stop playback requested by Spotify Connect", xbmc.LOGNOTICE)
            if not xbmc.getCondVisibility("Player.Paused"):
                xbmc.executebuiltin("PlayerControl(stop)")
            self.wfile.write("OK")
        self.wfile.close()
        return

    def auth_callback(self):
        '''callback for spotify authentication request'''
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Authentication succesfull</title></head>")
        self.wfile.write("<p>You can now close this browser window.</p>")
        self.wfile.write("</body></html>")
        self.wfile.close()
        xbmc.executebuiltin("SetProperty(spotify-token-info,%s,Home)" % self.path)
        return


class StoppableHttpServer (SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""
    pass
