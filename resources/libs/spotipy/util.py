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

    scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-modify user-follow-read user-library-read user-library-modify user-read-private user-read-email user-read-birthdate user-top-read"
    client_id = '4940f5cc79b149af9f71d5ef9319eff0'
    client_secret = '779f4d60bd3b42e29984adf423f19688'
    redirect_uri = 'http://localhost:%s/callback' %port
    
    #request the token
    cachepath=xbmc.translatePath(u"special://profile/addon_data/%s/%s.cache" % (ADDON_ID,normalize_string(username))).decode("utf-8")
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
        
        #launch webbrowser
        #try to find a browser...
        import webbrowser
        
        browser_path = None
        WINDOW.clearProperty("spotify-token_info")
        if xbmc.getCondVisibility("System.Platform.Android"):
            # for android we just launch the default android browser
            xbmc.executebuiltin("StartAndroidActivity(,android.intent.action.VIEW,,"+auth_url+")")
            browser_path = "android"
        elif webbrowser.open(auth_url, new=1):
            # use webbrowser module
            logMsg("Launching browser: autodetect")
            browser_path = "autodetect"
        else:
            # look for a browser on linux machines
            browser_path = None
            browsers = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/firefox"]
            if xbmc.getCondVisibility("System.HasAddon(browser.chromium)"):
                browsers.append(os.path.join(xbmcaddon.Addon('browser.chromium').getAddonInfo('path'), 'bin') + '/chromium')
            if xbmc.getCondVisibility("System.HasAddon(browser.chromium-browser)"):
                browsers.append(os.path.join(xbmcaddon.Addon('browser.chromium-browser').getAddonInfo('path'), 'bin') + '/chromium')
            for item in browsers:
                if xbmcvfs.exists(item):
                    browser_path = item
                    break
            if not browser_path:
                # No webbrowser found - try the manual way
                if xbmc.Dialog().yesno("No webbrowser detected", "The webbrowser could not be auto detected. Do you have one installed ?"):
                    browser_path = xbmc.Dialog().browse(2, "Executable of browser", 'files').decode("utf-8")

            if browser_path:
                #browser found, execute the browser and wait for our token
                logMsg("Launching browser " + browser_path)
                p = subprocess.Popen( [browser_path, auth_url], shell=False )
            

        if browser_path:

            count = 0
            while not WINDOW.getProperty("spotify-token_info"):
                logMsg("Waiting for authentication token...")
                xbmc.sleep(1000)
                if count == 120: break
                count += 1
                    
            response = WINDOW.getProperty("spotify-token_info")
            webService.stop()
            WINDOW.clearProperty("spotify-token_info")
            if response:
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
        except Exception as e: 
            logMsg("WebServer exception occurred " + str(e))
            
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
   