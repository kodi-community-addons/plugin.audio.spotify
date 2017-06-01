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


class WebService(threading.Thread):
    '''Main webservice class which holds the SimpleHTTPServer instance'''
    event = None
    exit = False

    def __init__(self, *args, **kwargs):
        self.event = threading.Event()
        self.sp = kwargs.get("sp")
        self.kodiplayer = kwargs.get("kodiplayer")
        self.spotty = kwargs.get("spotty")
        threading.Thread.__init__(self, *args)

    def stop(self):
        '''called when the thread needs to stop'''
        try:
            self.exit = True
            self.event.set()
            log_msg("Audio proxy - stop called")
            conn = httplib.HTTPConnection("127.0.0.1:%d" % PROXY_PORT)
            conn.request("QUIT", "/")
            conn.getresponse()
            kill_spotty()
        except Exception as exc:
            log_exception(__name__, exc)
        self.join(2)
        log_msg("Audio proxy - stopped")

    def run(self):
        '''called to start our webservice'''
        log_msg("start audio proxy on port %s" % PROXY_PORT, xbmc.LOGNOTICE)
        try:
            server = StoppableHttpServer(('127.0.0.1', PROXY_PORT), StoppableHttpRequestHandler)
            server.sp = self.sp
            server.kodiplayer = self.kodiplayer
            server.spotty = self.spotty
            server.serve_forever()
        except Exception as exc:
            log_exception("webservice.run", exc)


class Request(object):
    '''attributes from urlsplit that this class also sets'''
    uri_attrs = ('scheme', 'netloc', 'path', 'query', 'fragment')

    def __init__(self, uri, headers, rfile=None):
        self.uri = uri
        self.headers = headers
        parsed = urlparse.urlsplit(uri)
        for i, attr in enumerate(self.uri_attrs):
            setattr(self, attr, parsed[i])
        try:
            body_len = int(self.headers.get('Content-length', 0))
        except ValueError:
            body_len = 0
        if body_len and rfile:
            self.body = rfile.read(body_len)
        else:
            self.body = None


class StoppableHttpRequestHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):
    '''http request handler with QUIT stopping the server'''
    raw_requestline = ""
    protocol_version = 'HTTP/1.0'

    def __init__(self, request, client_address, server):
        try:
            SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception as exc:
            if not "10054" in str(exc):
                log_exception("requesthandler.init", exc)

    def do_QUIT(self):
        '''send 200 OK response, and set server.stop to True'''
        self.send_response(200)
        self.end_headers()
        self.server.stop = True

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
            self.send_header('Content-type', 'audio/x-wav')
            self.send_header('Transfer-Encoding', 'chunked')
            #self.send_header('Connection', 'Close')
        self.end_headers()

    def do_GET(self):
        '''send headers and reponse'''
        try:
            self.send_headers()
            if "callback" in self.path:
                self.auth_callback()
            elif "loadtrack" in self.path:
                self.server.sp.next_track()
                self.silence()
            elif "track" in self.path:
                self.single_track()
            elif "playercmd" in self.path:
                self.player_control()
        except Exception as exc:
            if not "timed out" in str(exc) and not "10054" in str(exc):
                log_exception("requesthandler.get", exc)
        return
        
    def write_chunk(self, chunk):
        tosend = '%X\r\n%s\r\n'%(len(chunk), chunk)
        self.wfile.write(tosend)

    def single_track(self):
        track_id = self.path.split("/")[-1]
        log_msg("Playback requested for track %s" %track_id)
        track_info = self.server.sp.track(track_id)
        duration = track_info["duration_ms"] / 1000
        wave_header, filesize = create_wave_header(duration)
        self.write_chunk(wave_header)
        self.wfile._sock.settimeout(duration)
        args = ["--disable-discovery", "--single-track", track_id]
        spotty = self.server.spotty.run_spotty(arguments=args)
        bytes_written = 0
        try:
            line = spotty.stdout.readline()
            while line and not self.server.stop and bytes_written < filesize:
                bytes_written += len(line)
                self.write_chunk(line)
                line = spotty.stdout.readline()
            # stream some silence untill end is reached
            while bytes_written < filesize and not self.server.stop:
                bytes_written += 4096
                self.write_chunk('\0' * 4096)
        except Exception as exc:
            log_msg(exc, xbmc.LOGDEBUG)
        finally:
            spotty.terminate()
            del spotty
        self.wfile.write('0\r\n\r\n')
    
    def silence(self, duration=20):
        self.wfile._sock.settimeout(duration)
        wave_header, filesize = create_wave_header(duration)
        self.write_chunk(wave_header)
        bytes_written = 0
        while bytes_written < filesize and not self.server.stop:
            bytes_written += 4096
            self.write_chunk('\0' * 4096)
        self.wfile.write('0\r\n\r\n')
        
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

    def serve_forever(self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()

    # def finish_request(self, request, client_address):
        # request.settimeout(30)
        # BaseHTTPServer.HTTPServer.finish_request(self, request, client_address)


def stop_server(port):
    """send QUIT request to http server running on localhost:<port>"""
    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()
