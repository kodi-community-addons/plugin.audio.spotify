# -*- coding: utf8 -*-
import threading
import thread
import time
import re
import struct
import cherrypy
from cherrypy._cpnative_server import CPHTTPServer
from datetime import datetime
import random
import sys
import platform
import logging
import os
from utils import log_msg, log_exception, create_wave_header, PROXY_PORT, StringIO
import xbmc


class Root:
    spotty = None

    def __init__(self, spotty):
        self.__spotty = spotty

    def _check_request(self):
        method = cherrypy.request.method.upper()
        headers = cherrypy.request.headers
        # Fail for other methods than get or head
        if method not in ("GET", "HEAD"):
            raise cherrypy.HTTPError(405)
        # Error if the requester is not allowed
        # for now this is a simple check just checking if the useragent matches Kodi
        user_agent = headers['User-Agent'].lower()
        if not ("kodi" in user_agent or "osmc" in user_agent):
            raise cherrypy.HTTPError(403)
        return method

    @cherrypy.expose
    def track(self, track_id, duration, **kwargs):
        # Check sanity of the request
        self._check_request()

        # Calculate file size, and obtain the header
        duration = int(duration)
        wave_header, filesize = create_wave_header(duration)
        request_range = cherrypy.request.headers.get('Range', '')
        range_l = 0
        range_r = filesize

        # headers
        if request_range and request_range != "bytes=0-":
            # partial request
            cherrypy.response.status = '206 Partial Content'
            cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
            range = cherrypy.request.headers["Range"].split("bytes=")[1].split("-")
            range_l = int(range[0])
            try:
                range_r = int(range[1])
            except:
                range_r = filesize
            chunk = range_r - range_l
            cherrypy.response.headers['Accept-Ranges'] = 'bytes'
            cherrypy.response.headers['Content-Length'] = chunk
            cherrypy.response.headers['Content-Range'] = "bytes %s-%s/%s" % (range_l, range_r, filesize)
        else:
            # full file
            cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
            cherrypy.response.headers['Accept-Ranges'] = 'bytes'
            cherrypy.response.headers['Content-Length'] = filesize

        # If method was GET, write the file content
        if cherrypy.request.method.upper() == 'GET':
            return self.send_audio_stream(track_id, filesize, wave_header, range_l)
    track._cp_config = {'response.stream': True}

    def send_audio_stream(self, track_id, filesize, wave_header, range_l):
        '''chunked transfer of audio data from spotty binary'''
        log_msg("start transfer for track %s - range: %s" % (track_id, range_l), xbmc.LOGDEBUG)
        spotty_bin = None
        try:
            # Initialize some loop vars
            max_buffer_size = 524288
            bytes_written = 0

            # Write wave header
            bytes_written = len(wave_header)
            if not range_l:
                yield wave_header

            # get pcm data from spotty stdout and append to our buffer
            args = ["-n", "temp", "--single-track", track_id]
            spotty_bin = self.__spotty.run_spotty(args)
            
            # ignore the first x bytes to match the range request
            if range_l:
                spotty_bin.stdout.read(range_l - bytes_written)

            # Loop as long as there's something to output
            frame = spotty_bin.stdout.read(max_buffer_size)
            while frame:
                if cherrypy.response.timed_out:
                    log_msg("response timeout !", xbmc.LOGDEBUG)
                    break
                bytes_written += len(frame)
                yield frame
                frame = spotty_bin.stdout.read(max_buffer_size)

            # Add some silence padding until the end is reached (if needed)
            while bytes_written < filesize:
                if bytes_written + max_buffer_size < filesize:
                    # The buffer size fits into the file size
                    yield '\0' * max_buffer_size
                    bytes_written += max_buffer_size
                else:
                    # Does not fit, just generate the remaining bytes
                    yield '\0' * (filesize - bytes_written)
                    bytes_written = filesize
        except Exception as exc:
            log_exception(__name__, exc)
        finally:
            # make sure spotty always gets terminated
            if spotty_bin:
                spotty_bin.terminate()
            log_msg("FINISH transfer for track %s - range %s" % (track_id, range_l), xbmc.LOGDEBUG)

    @cherrypy.expose
    def silence(self, duration, **kwargs):
        '''stream silence audio for the given duration, used by spotify connect player'''
        duration = int(duration)
        wave_header, filesize = create_wave_header(duration)
        output_buffer = StringIO()
        output_buffer.write(wave_header)
        output_buffer.write('\0' * (filesize - output_buffer.tell()))
        return cherrypy.lib.static.serve_fileobj(output_buffer, content_type="audio/wav",
                                                 name="%s.wav" % duration, filesize=output_buffer.tell())

    @cherrypy.expose
    def nexttrack(self, **kwargs):
        '''play silence while spotify connect player is waiting for the next track'''
        return self.silence(20)

    @cherrypy.expose
    def callback(self, **kwargs):
        cherrypy.response.headers['Content-Type'] = 'text/html'
        code = kwargs.get("code")
        url = "http://localhost:%s/callback?code=%s" % (PROXY_PORT, code)
        if cherrypy.request.method.upper() in ['GET', 'POST']:
            html = "<html><body><h1>Authentication succesfull</h1>"
            html += "<p>You can now close this browser window.</p>"
            html += "</body></html>"
            xbmc.executebuiltin("SetProperty(spotify-token-info,%s,Home)" % url)
            log_msg("authkey sent")
            return html
    
    @cherrypy.expose
    def playercmd(self, cmd, **kwargs):
        if cmd == "start":
            cherrypy.response.headers['Content-Type'] = 'text'
            log_msg("playback start requested by connect")
            xbmc.executebuiltin("RunPlugin(plugin://plugin.audio.spotify/?action=play_connect)")
            return "OK"
        elif cmd == "stop":
            cherrypy.response.headers['Content-Type'] = 'text'
            log_msg("playback stop requested by connect")
            xbmc.executebuiltin("PlayerControl(Stop)")
            return "OK"

class ProxyRunner(threading.Thread):
    __server = None
    __root = None

    def __init__(self, spotty):
        self.__root = Root(spotty)
        cherrypy.config.update({
            'engine.timeout_monitor.frequency': 5,
            'server.shutdown_timeout': 1,
            'engine.autoreload.on' : False,
            'log.screen': False,
        })
        self.__server = cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)
        threading.Thread.__init__(self)

    def run(self):
        conf = {
            'global': {
                'server.socket_host': '0.0.0.0',
                'server.socket_port': PROXY_PORT
            }, '/': {}
        }
        cherrypy.quickstart(self.__root, '/', conf)

    def get_port(self):
        return self.__server.bind_addr[1]

    def get_host(self):
        return self.__server.bind_addr[0]

    def stop(self):
        cherrypy.engine.exit()
        self.join(0)
        del self.__root
        del self.__server
