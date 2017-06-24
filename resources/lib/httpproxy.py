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
from utils import log_msg, log_exception, create_wave_header, kill_librespot, PROXY_PORT, parse_spotify_track, StringIO
import xbmc


class Track:
    __allowed_ips = None

    def __init__(self, librespot, allowed_ips, cur_buffer):
        self.__allowed_ips = allowed_ips
        self.__librespot = librespot
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
            output_buffer = self.__cur_buffer[1]
            filesize = self.__cur_buffer[2]
        else:
            # parse duration and generate wave header
            duration = int(duration)
            wave_header, filesize = create_wave_header(duration)
            output_buffer = StringIO()
            output_buffer.write(wave_header)      
            # get pcm data from librespot stdout and append to our buffer
            args = ["-n", "temp", "--single-track", track_id, "--backend", "pipe"]
            librespot_bin = self.__librespot.run_librespot(args)
            stdout, stderr = librespot_bin.communicate()
            output_buffer.write(stdout)
            output_buffer.seek(0)
            self.__cur_buffer = (track_id, output_buffer, filesize)
        return cherrypy.lib.static.serve_fileobj(output_buffer, content_type="audio/wav", 
                name="%s.wav" % track_id, filesize=filesize)
                
                
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
            
class Root:
    track = None
    callback = None
    cur_buffer = None

    def __init__(self, librespot):
        allowed_ips = ['127.0.0.1']
        self.track = Track( librespot, allowed_ips, self.cur_buffer )
        self.callback = AuthCallback()

    def cleanup(self):
        self.track = None
        self.callback = None


class ProxyRunner(threading.Thread):
    __server = None
    __root = None

    def __init__(self, librespot):
        host='127.0.0.1'
        port = PROXY_PORT
        self.__root = Root( librespot )
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
