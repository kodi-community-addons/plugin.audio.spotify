from __future__ import print_function, unicode_literals
import SimpleHTTPServer, BaseHTTPServer, httplib
import threading
import thread
import urlparse
from utils import *
import xbmc,xbmcvfs
import os,signal
import subprocess
from . import oauth2
import spotipy
port = 52308

def prompt_for_user_token(username, scope=None, client_id = None,
        client_secret = None, redirect_uri = None):

    scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-modify user-follow-read user-library-read user-library-modify user-read-private user-read-email user-read-birthdate"
    client_id = '4940f5cc79b149af9f71d5ef9319eff0'
    client_secret = '779f4d60bd3b42e29984adf423f19688'
    redirect_uri = 'http://localhost:%s/callback' %port
    
    #request the token
    cachepath=xbmc.translatePath("special://profile/addon_data/%s/%s.cache" % (ADDON_ID,username)).decode("utf-8")
    sp_oauth = oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, 
        scope=scope, cache_path=cachepath )

    # try to get a valid token for this user, from the cache,
    # if not in the cache, then create a new (this will send
    # the user to a web page where they can authorize this app)

    token_info = sp_oauth.get_cached_token()

    if not token_info:
        p = None
        webService = WebService()
        webService.start()
        xbmc.sleep(1000) #allow the webservice to start
        
        auth_url = sp_oauth.get_authorize_url()
        
        if xbmc.getCondVisibility("System.Platform.Android"):
            xbmc.executebuiltin("StartAndroidActivity(com.android.chrome,android.intent.action.VIEW,,"+auth_url+")")
            browser = "android"
        elif xbmc.getCondVisibility("System.HasAddon(browser.chromium)"):
            #openelec chromium browser
            chromium_path  = os.path.join(xbmcaddon.Addon('browser.chromium').getAddonInfo('path'), 'bin') + '/chromium'
            p = subprocess.Popen( [chromium_path,auth_url],shell=False )
            browser = 'chromium_path'
            logMsg("Launching browser " + browser)
        else:
            #try to find a browser...
            browsers = []
            browser = ""
            browsers.append("c:\program files (x86)\Google\Chrome\Application\chrome.exe")
            browsers.append("c:\program files\Google\Chrome\Application\chrome.exe")
            browsers.append("c:\program files (x86)\Internet Explorer\iexplore.exe")
            browsers.append("c:\program files\Internet Explorer\iexplore.exe")
            browsers.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            browsers.append("/usr/bin/google-chrome")
            browsers.append("/usr/bin/chromium-browser")
            for item in browsers:
                if xbmcvfs.exists(item):
                    browser = item
                    #browser found, execute the browser and wait for our token
                    WINDOW.clearProperty("spotify-token_info")
                    logMsg("Launching browser " + browser)
                    p = subprocess.Popen( [browser,auth_url],shell=False )
                    break
                
        if not browser:
            WINDOW.setProperty("Spotify.Lasterror", ADDON.getLocalizedString(11003))
        else:
            #wait for token...
            count = 0
            while not WINDOW.getProperty("spotify-token_info"):
                logMsg("Waiting for authentication token...")
                xbmc.sleep(1000)
                if count == 120: break
                count += 1
                
            #close browser
            try: 
                p.terminate()
                p.kill()
            except: 
                pass
                
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
        logMsg("WebService - start helper webservice on port %s" %port)
        self.event =  threading.Event()
        threading.Thread.__init__(self, *args)
    
    def stop(self):
        try:
            logMsg("WebService - stop called")
            conn = httplib.HTTPConnection("127.0.0.1:%d" % port)
            conn.request("QUIT", "/")
            conn.getresponse()
            self.exit = True
            self.event.set()
        except Exception as e: logMsg("WebServer exception occurred " + str(e))

    def run(self):
        try:
            server = StoppableHttpServer(('127.0.0.1', port), StoppableHttpRequestHandler)
            server.serve_forever()
        except Exception as e: logMsg("WebServer exception occurred " + str(e))
            
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
        except Exception as e: logMsg("WebServer error in request --> " + str(e))
    
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
        logMsg("WebServer GET --> " + self.path)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><head><title>Authentication succesfull</title></head>")
        self.wfile.write("<p>You can now close this browser window.</p>")
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
   