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
from utils import log_msg, log_exception, create_wave_header, PROXY_PORT, StringIO
from utils import NonBlockingStreamReader as NBSR
import xbmc


class Track:
    __allowed_ips = None

    def __init__(self, spotty, allowed_ips, cur_buffer):
        self.__allowed_ips = allowed_ips
        self.__spotty = spotty

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
            if range_l:
                # range requested - only send the requested range data
                log_msg("send requested range for track %s - range: %s" % (track_id, range_l), xbmc.LOGDEBUG)
                return self.partial_audio_stream(track_id, filesize, wave_header, range_l, range_r)
            else:
                # chunked transfer of full track
                log_msg("start chunked transfer for full track %s" % track_id, xbmc.LOGDEBUG)
                return self.chunked_audio_stream(track_id, filesize, wave_header)
    default._cp_config = {'response.stream': True}
        
    def chunked_audio_stream(self, track_id, filesize, wave_header):
        '''chunked transfer of audio data from spotty binary'''
        #Initialize some loop vars
        max_buffer_size=65535
        output_buffer = StringIO()
        bytes_written = 0
        has_frames = True

        #Write wave header
        output_buffer.write(wave_header)
        bytes_written = output_buffer.tell()
        yield wave_header
        output_buffer.truncate(0)
            
        # get pcm data from spotty stdout and append to our buffer
        args = ["-n", "temp", "--single-track", track_id]
        spotty_bin = self.__spotty.run_spotty(args)
        nbsr = NBSR(spotty_bin.stdout)

        #Loop as long as there's something to output
        frame = nbsr.readline(5)
        while has_frames:
            try:
                #Check if this frame fits in the estimated calculation
                if bytes_written + len(frame) < filesize:
                    output_buffer.write(frame)
                    bytes_written += len(frame)
                else:
                    #Does not fit, we need to truncate the frame data
                    truncate_size = filesize - bytes_written
                    output_buffer.write(frame[:truncate_size])
                    bytes_written = filesize
                    has_frames = False
                frame = nbsr.readline(0.5)
            except Exception as exc:
                log_exception(__name__, exc)
                has_frames = False
            finally:
                #Check if the current buffer needs to be flushed
                if not has_frames or output_buffer.tell() > max_buffer_size:
                    yield output_buffer.getvalue()
                    output_buffer.truncate(0)

        #Add some silence padding until the end is reached (if needed)
        while bytes_written < filesize:
            if bytes_written + max_buffer_size < filesize:
                #The buffer size fits into the file size
                yield '\0' * max_buffer_size
                bytes_written += max_buffer_size
            else:
                #Does not fit, just generate the remaining bytes
                yield '\0' * (filesize - bytes_written)
                memory_buffer.write(frame)
                bytes_written = filesize

    def partial_audio_stream(self, track_id, filesize, wave_header, range_l, range_r):
        '''send partial data from track'''
        output_buffer = StringIO()

        #Write wave header
        output_buffer.write(wave_header)
            
        # get pcm data from spotty stdout and append to our buffer
        args = ["-n", "temp", "--single-track", track_id]
        spotty_bin = self.__spotty.run_spotty(args)
        stdout, stderr = spotty_bin.communicate()
        output_buffer.write(stdout)
        
        # truncate or add silence padding if needed
        if output_buffer.tell() > filesize:
            output_buffer.truncate(filesize)
        elif output_buffer.tell() < filesize:
            frame = '\0' * (filesize - output_buffer.tell())
            output_buffer.write(frame)
        
        # finally send the requested range
        yield output_buffer.getvalue()[range_l:range_r]
        del output_buffer
    
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
