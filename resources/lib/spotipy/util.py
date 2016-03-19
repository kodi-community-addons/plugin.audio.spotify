
# shows a user's playlists (need to be authenticated via oauth)
from __future__ import print_function
import SimpleHTTPServer, BaseHTTPServer, httplib
import threading
import thread
import urlparse
from __main__ import ADDON_ID,SETTING,WINDOW
import xbmc
import os
import subprocess
from . import oauth2
import spotipy
port = 52308

def prompt_for_user_token(username, scope=None, client_id = None,
        client_secret = None, redirect_uri = None):

    scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-modify user-follow-read user-library-read user-library-modify"
    client_id = '4940f5cc79b149af9f71d5ef9319eff0'
    client_secret = '779f4d60bd3b42e29984adf423f19688'
    redirect_uri = 'http://localhost:%s/callback' %port
    
    #request the token
    cachepath=xbmc.translatePath("special://profile/addon_data/%s/%s.cache" % (ADDON_ID,username)).decode("utf-8")
    sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, 
        scope=scope, cache_path=cachepath )

    # try to get a valid token for this user, from the cache,
    # if not in the cache, the create a new (this will send
    # the user to a web page where they can authorize this app)

    token_info = sp_oauth.get_cached_token()

    if not token_info:
    
        webService = WebService()
        webService.start()
        
        auth_url = sp_oauth.get_authorize_url()
        subprocess.call(["C:\Program Files (x86)\Internet Explorer\iexplore.exe", auth_url])
        
        #wait for token...
        while not WINDOW.getProperty("spotify-token_info"):
            xbmc.sleep(1000)
            
        response = WINDOW.getProperty("spotify-token_info")
        webService.stop()
        WINDOW.clearProperty("spotify-token_info")
        
        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code)
    
    # Auth'ed API request
    if token_info:
        return token_info['access_token']
    else:
        return None

        
        
class WebService(threading.Thread):
    event = None
    exit = False
    
    def __init__(self, *args):
        print ("WebService - start helper webservice on port %s" %port)
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)
    
    def stop(self):
        try:
            print ("WebService - stop called")
            conn = httplib.HTTPConnection("127.0.0.1:%d" % port)
            conn.request("QUIT", "/")
            conn.getresponse()
            self.exit = True
            self.event.set()
        except Exception as e: print ("WebServer exception occurred " + str(e))

    def run(self):
        try:
            server = StoppableHttpServer(('127.0.0.1', port), StoppableHttpRequestHandler)
            server.serve_forever()
        except Exception as e: print ("WebServer exception occurred " + str(e))
            
class Request(object):
    # attributes from urlsplit that this class also sets
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
    #http request handler with QUIT stopping the server
    
    def __init__(self, request, client_address, server):
        try:
            SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception as e: print("WebServer error in request --> " + str(e))
    
    def do_QUIT (self):
        #send 200 OK response, and set server.stop to True
        self.send_response(200)
        self.end_headers()
        self.server.stop = True
    
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        print(self.wfile)
        self.wfile.write("<html><head><title>Title goes here.</title></head>")
        self.wfile.write("<p>You accessed path: %s</p>" % self.path)
        self.wfile.write("</body></html>")
        self.wfile.close()
        if "QUIT" in self.path:
            self.server.stop = True
        if "callback" in self.path:
            token = self.path.split("code=")[1]
            WINDOW.setProperty("spotify-token_info", self.path)


class StoppableHttpServer (BaseHTTPServer.HTTPServer):
    """http server that reacts to self.stop flag"""

    def serve_forever (self):
        """Handle one request at a time until stopped."""
        self.stop = False
        while not self.stop:
            self.handle_request()


def stop_server (port):
    """send QUIT request to http server running on localhost:<port>"""
    conn = httplib.HTTPConnection("localhost:%d" % port)
    conn.request("QUIT", "/")
    conn.getresponse()
   