#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception
import xbmc
import threading
import _thread
import xbmcvfs


class ConnectDaemon(threading.Thread):
    '''Simulate a Spotify Connect player with the Kodi player'''
    daemon_active = False
    __exit = False
    __spotty_proc = None

    def __init__(self, spotty):
        self.__spotty = spotty
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def stop(self):
        '''cleanup on exit'''
        self.__exit = True
        if self.__spotty_proc:
            self.__spotty_proc.terminate()
            log_msg("spotty terminated")
            self.join(2)

    def run(self):
        log_msg("Start Spotify Connect Daemon")
        self.__exit = False
        self.daemon_active = True
        spotty_args = ["--lms", "localhost:52308/", "--player-mac", "None"]
        disable_discovery = False
        if xbmcvfs.exists("/run/libreelec/"):
            disable_discovery = True # avahi on libreelec conflicts with the mdns implementation of librespot
            xbmc.executebuiltin("SetProperty(spotify-discovery,disabled,Home)")
        try:
            try:
                log_msg("trying AP Port 443", xbmc.LOGINFO)
                self.__spotty_proc = self.__spotty.run_spotty(arguments=spotty_args, disable_discovery=disable_discovery, ap_port="443")
            except:
                try:
                    log_msg("trying AP Port 80", xbmc.LOGINFO)                    
                    self.__spotty_proc = self.__spotty.run_spotty(arguments=spotty_args, disable_discovery=disable_discovery, ap_port="80")
                except:
                    log_msg("trying AP Port 4070", xbmc.LOGINFO)                    
                    self.__spotty_proc = self.__spotty.run_spotty(arguments=spotty_args, disable_discovery=disable_discovery, ap_port="4070")                
            while not self.__exit:
                line = self.__spotty_proc.stdout.readline()
                if self.__spotty_proc.returncode and self.__spotty_proc.returncode > 0 and not self.__exit:
                    # daemon crashed ? restart ?
                    log_msg("spotty stopped!", xbmc.LOGINFO)
                    break
                xbmc.sleep(100)
            self.daemon_active = False
            log_msg("Stopped Spotify Connect Daemon")        
        except:
            self.daemon_active = False
            log_msg("Cannot run SPOTTY, No APs available", xbmc.LOGINFO)


