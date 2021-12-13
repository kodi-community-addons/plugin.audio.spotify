# -*- coding: utf-8 -*-
import threading
import _thread
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
from io import BytesIO
from utils import log_msg, log_exception, create_wave_header, PROXY_PORT, StringIO
import xbmc
import math

class Root:
    spotty = None
    spotty_bin = None
    spotty_trackid = None
    spotty_range_l = None
    
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
        # if not ("Kodi" in user_agent or "osmc" in user_agent):
        #     raise cherrypy.HTTPError(403)
        return method


    @cherrypy.expose
    def index(self): 
        return "Server started"	

    # @cherrypy.expose   
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()  
    def lms(self, filename, **kwargs):
        ''' fake lms hook to retrieve events from spotty daemon'''
        method = cherrypy.request.method.upper()
        if method != "POST" or filename != "jsonrpc.js":
            raise cherrypy.HTTPError(405)
        input_json = cherrypy.request.json
        if input_json and input_json.get("params"):
            event = input_json["params"][1]
            log_msg("lms event hook called. Event: %s" % event)
            # check username, it might have changed
            spotty_user = self.__spotty.get_username()
            cur_user = xbmc.getInfoLabel("Window(Home).Property(spotify-username)")
            if spotty_user != cur_user:
                log_msg("user change detected")
                xbmc.executebuiltin("SetProperty(spotify-cmd,__LOGOUT__,Home)")
            if "start" in event:
                log_msg("playback start requested by connect")
                xbmc.executebuiltin("RunPlugin(plugin://plugin.audio.spotify/?action=play_connect)")
            elif "change" in event:
                log_msg("playback change requested by connect")
                # we ignore this as track changes are 
                #xbmc.executebuiltin("RunPlugin(plugin://plugin.audio.spotify/?action=play_connect)")
            elif "stop" in event:
                log_msg("playback stop requested by connect")
                xbmc.executebuiltin("PlayerControl(Stop)")
            elif "volume" in event:
                vol_level = event[2]
                log_msg("volume change detected on connect player: %s" % vol_level)
                # ignore for now as it needs more work
                #xbmc.executebuiltin("SetVolume(%s,true)" % vol_level)
        return {"operation": "request", "result": "success"}

    @cherrypy.expose
    def track(self, track_id, duration, **kwargs):
        # Check sanity of the request
        self._check_request()

        # Calculate file size, and obtain the header
        duration = int(float(duration))
        wave_header, filesize = create_wave_header(duration)
        request_range = cherrypy.request.headers.get('Range', '')
        # response timeout must be at least the duration of the track: read/write loop
        # checks for timeout and stops pushing audio to player if it occurs
        cherrypy.response.timeout =  int(math.ceil(duration * 1.5))
    
        range_l = 0
        range_r = filesize

        # headers
        if request_range and request_range != "bytes=0-":
            # partial request
            cherrypy.response.status = '206 Partial Content'
            cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
            range = cherrypy.request.headers["Range"].split("bytes=")[1].split("-")
            log_msg("request header range: %s" % (cherrypy.request.headers['Range']), xbmc.LOGDEBUG)
            range_l = int(range[0])
            try:
                range_r = int(range[1])
            except:
                range_r = filesize

            cherrypy.response.headers['Accept-Ranges'] = 'bytes'
            cherrypy.response.headers['Content-Length'] = range_r - range_l
            cherrypy.response.headers['Content-Range'] = "bytes %s-%s/%s" % (range_l, range_r, filesize)
            log_msg("partial request range: %s, length: %s" % (cherrypy.response.headers['Content-Range'], cherrypy.response.headers['Content-Length']), xbmc.LOGDEBUG)
        else:
            # full file
            cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
            cherrypy.response.headers['Accept-Ranges'] = 'bytes'
            cherrypy.response.headers['Content-Length'] = filesize
            log_msg("!! Full File. Size : %s " % (filesize), xbmc.LOGDEBUG)

        # If method was GET, write the file content
        if cherrypy.request.method.upper() == 'GET':
        
            if self.spotty_bin != None:
                # If spotty binary still attached for a different request, try to terminate it.
                log_msg("WHOOPS!!! Running spotty detected - killing it to continue.", \
                    xbmc.LOGERROR)
                self.kill_spotty()
                
            while self.spotty_bin:
                time.sleep(0.1)
            
            return self.send_audio_stream(track_id, range_r - range_l, wave_header, range_l)
        
    track._cp_config = {'response.stream': True}

    def kill_spotty(self):
        self.spotty_bin.terminate()
        self.spotty_bin.communicate()
        self.spotty_bin = None
        self.spotty_trackid = None
        self.spotty_range_l = None

    def send_audio_stream(self, track_id, length, wave_header, range_l):
        '''chunked transfer of audio data from spotty binary'''
        try:
            log_msg("start transfer for track %s - range: %s" % (track_id, range_l), \
                xbmc.LOGDEBUG)
                    
            # Initialize some loop vars
            max_buffer_size = 524288
            bytes_written = 0

            # Write wave header
            # only count bytes actually from the spotify stream
            # bytes_written = len(wave_header)
            if not range_l:
                yield wave_header
                bytes_written = len(wave_header)

            # get OGG data from spotty stdout and append to our buffer
            args = ["-n", "temp", "--single-track", track_id]
            if self.spotty_bin == None:
                self.spotty_bin = self.__spotty.run_spotty(args, use_creds=True)
            self.spotty_trackid = track_id
            self.spotty_range_l = range_l
            log_msg("Infos : Track : %s" % track_id)
			
			
	        # ignore the first x bytes to match the range request
            if range_l:
                self.spotty_bin.stdout.read(range_l)

            # Loop as long as there's something to output
            while bytes_written < length:
                frame = self.spotty_bin.stdout.read(max_buffer_size)
                if not frame:
                    break
                bytes_written += len(frame)
                yield frame

            log_msg("FINISH transfer for track %s - range %s - written %s" % (track_id, range_l, bytes_written), \
                     xbmc.LOGDEBUG)
        except Exception as exc:
            log_exception(__name__, exc)
            log_msg("EXCEPTION FINISH transfer for track %s - range %s - written %s" % (track_id, range_l, bytes_written), \
                    xbmc.LOGDEBUG)
        finally:
            # make sure spotty always gets terminated
            if self.spotty_bin != None:
                self.kill_spotty()

    @cherrypy.expose
    def silence(self, duration, **kwargs):
        '''stream silence audio for the given duration, used by spotify connect player'''
        duration = float(duration)
        wave_header, filesize = create_wave_header(duration)
        output_buffer = BytesIO()
        output_buffer.write(wave_header)
        output_buffer.write(bytes('\0' * (filesize - output_buffer.tell()), 'utf-8'))
        return cherrypy.lib.static.serve_fileobj(output_buffer.read(), content_type="audio/wav", name="%s.wav" % duration, debug=True)

    @cherrypy.expose
    def nexttrack(self, **kwargs):
        '''play silence while spotify connect player is waiting for the next track'''
        log_msg('play silence while spotify connect player is waiting for the next track', xbmc.LOGDEBUG)
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
        log = cherrypy.log
        log.screen = True
        cherrypy.config.update({
            'server.socket_host': '127.0.0.1',
            'server.socket_port': PROXY_PORT
        })
        self.__server = cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)
        threading.Thread.__init__(self)

    def run(self):
        conf = { '/': {}}
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
