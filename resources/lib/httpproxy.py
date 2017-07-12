# -*- coding: utf8 -*-
import threading
import time
import re
import struct
import cherrypy
from cherrypy import wsgiserver
from cherrypy.process import servers
from datetime import datetime
import random
import sys
import platform
import logging
import os
from utils import log_msg, log_exception, create_wave_header, kill_spotty, PROXY_PORT, parse_spotify_track, StringIO
from utils import NonBlockingStreamReader as NBSR
import xbmc


class Track:
    __allowed_ips = None

    def __init__(self, spotty, allowed_ips, cur_buffer):
        self.__allowed_ips = allowed_ips
        self.__spotty = spotty
        self.__cur_buffer = cur_buffer

    def _check_request(self):
        method = cherrypy.request.method.upper()
        headers = cherrypy.request.headers
        # Fail for other methods than get or head
        if method not in ("GET", "HEAD"):
            raise cherrypy.HTTPError(405)
        # Error if the requester is not allowed
        if headers['Remote-Addr'] not in self.__allowed_ips:
            raise cherrypy.HTTPError(403)
        return method

    @cherrypy.expose
    def default(self, track_id, duration, **kwargs):
        # Check sanity of the request
        self._check_request()
        # first check if track is already in our buffer
        if self.__cur_buffer and self.__cur_buffer[0] == track_id:
            # track is already buffered, send the trackdata all at once
            output_buffer = self.__cur_buffer[1]
            filesize = self.__cur_buffer[2]
            yield output_buffer.getvalue()
        else:
            # track data is not yet buffered, start buffering and chunked streaming
            duration = int(duration)
            wave_header, filesize = create_wave_header(duration)
            cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
            cherrypy.response.headers['Content-Length'] = filesize
            output_buffer = StringIO()
            output_buffer.write(wave_header)
            yield wave_header
            bytes_written = 0
            # get pcm data from spotty stdout and append to our buffer
            args = ["-n", "temp", "--single-track", track_id]
            spotty_bin = self.__spotty.run_spotty(args)
            nbsr = NBSR(spotty_bin.stdout)
            log_msg("start streaming of track %s" % track_id)
            output = nbsr.readline(2)
            while output:
                output_buffer.write(output)
                yield output
                output = nbsr.readline(0.1)
            log_msg("end of stream for track %s" % track_id)
            self.__cur_buffer = (track_id, output_buffer, filesize)
            log_msg(spotty_bin.stderr.readlines())
    default._cp_config = {'response.stream': True}
        
    @cherrypy.expose
    def silence(self, duration, **kwargs):
        '''stream silence audio for the given duration, used by fake connect player'''
        duration = int(duration)
        wave_header, filesize = create_wave_header(duration)
        output_buffer = StringIO()
        output_buffer.write(wave_header)
        output_buffer.write('\0' * filesize)
        return cherrypy.lib.static.serve_fileobj(output_buffer, content_type="audio/wav",
                name="%s.wav" % duration, filesize=filesize)
            
    @cherrypy.expose
    def nexttrack(self, **kwargs):
        '''tell spotify connect to move to the next track and play silence while waiting'''
        return self.silence(20)
             
    
class AuthCallback:
    @cherrypy.expose
    def default(self, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'text/html'
        code = kwargs.get("code")
        url = "http://localhost:%s/callback?code=%s" %(PROXY_PORT, code)
        if cherrypy.request.method.upper() in ['GET', 'POST']:
            html = "<html><body><h1>Authentication succesfull</h1>"
            html += "<p>You can now close this browser window.</p>"
            html += "</body></html>"
            xbmc.executebuiltin("SetProperty(spotify-token-info,%s,Home)" % url)
            log_msg("authkey sent")
            return html
            
class PlayerCmd:
    @cherrypy.expose
    def start(self, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'text'
        log_msg("playback start requested by connect")
        xbmc.executebuiltin("PlayMedia(plugin://plugin.audio.spotify/?action=play_connect)")
        return "OK"
        
    @cherrypy.expose
    def stop(self, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'text'
        log_msg("playback stop requested by connect")
        xbmc.executebuiltin("PlayerControl(Stop)")
        return "OK"
            
class Root:
    track = None
    callback = None
    cur_buffer = None

    def __init__(self, spotty):
        allowed_ips = ['localhost', '::1', '127.0.0.1']
        self.track = Track( spotty, allowed_ips, self.cur_buffer )
        self.callback = AuthCallback()
        self.playercmd = PlayerCmd()

    def cleanup(self):
        self.track = None
        self.callback = None
        self.playercmd = None


class ProxyRunner(threading.Thread):
    __server = None
    __root = None

    def __init__(self, spotty):
        host='0.0.0.0'
        port = PROXY_PORT
        self.__root = Root( spotty )
        app = cherrypy.tree.mount(self.__root, '/')
        log = cherrypy.log
        log.access_file = ''
        log.error_file = ''
        log.screen = True
        self.__server = wsgiserver.CherryPyWSGIServer((host, port), app)
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        self.__server.start()

    def get_port(self):
        return self.__server.bind_addr[1]

    def get_host(self):
        return self.__server.bind_addr[0]

    def ready_wait(self):
        while not self.__server.ready:
            time.sleep(.1)

    def stop(self):
        self.__server.stop()
        self.join(2)
        self.__root.cleanup()
