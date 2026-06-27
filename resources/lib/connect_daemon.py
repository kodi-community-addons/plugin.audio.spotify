#!/usr/bin/python
# -*- coding: utf-8 -*-


from utils import log_msg, log_exception
import xbmc
import threading
import thread
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
        # Removed obsolete --lms and --player-mac arguments; these flags are not
        # supported by current spotty/librespot builds and cause immediate exit.
        spotty_args = []
        disable_discovery = False
        if xbmcvfs.exists("/run/libreelec/"):
            disable_discovery = True  # avahi on libreelec conflicts with the mdns implementation of librespot
            xbmc.executebuiltin("SetProperty(spotify-discovery,disabled,Home)")

        ap_ports = ["443", "80", "4070"]
        retry_delay = 5  # seconds to wait before restarting after a crash

        def start_spotty():
            """Try each AP port in turn; return the first process that starts."""
            for port in ap_ports:
                try:
                    log_msg("trying AP Port %s" % port, xbmc.LOGNOTICE)
                    proc = self.__spotty.run_spotty(
                        arguments=spotty_args,
                        disable_discovery=disable_discovery,
                        ap_port=port,
                    )
                    if proc is not None:
                        return proc
                except Exception as exc:
                    log_msg("AP Port %s failed: %s" % (port, exc), xbmc.LOGNOTICE)
            return None

        try:
            self.__spotty_proc = start_spotty()
            if self.__spotty_proc is None:
                raise RuntimeError("All AP ports exhausted — cannot start spotty")

            while not self.__exit:
                line = self.__spotty_proc.stdout.readline()
                # readline() returns b'' on EOF when the process has exited.
                if not line:
                    self.__spotty_proc.poll()
                    if not self.__exit:
                        rc = self.__spotty_proc.returncode
                        # A non-zero exit often means spotty hit a non-206 CDN
                        # response (e.g. HTTP 500 on the first CDN URL) and gave
                        # up.  Restart so librespot can retry with a fresh set of
                        # CDN URLs — mirroring the upstream fix in librespot
                        # commit db1ef7ab8c5ebd78edea0ba20f34feb21bd0e195.
                        log_msg(
                            "spotty exited (rc=%s) — restarting in %ss" % (rc, retry_delay),
                            xbmc.LOGNOTICE,
                        )
                        xbmc.sleep(retry_delay * 1000)
                        if not self.__exit:
                            self.__spotty_proc = start_spotty()
                            if self.__spotty_proc is None:
                                log_msg("Cannot restart spotty, giving up", xbmc.LOGERROR)
                                break
                    continue
                xbmc.sleep(100)

            self.daemon_active = False
            log_msg("Stopped Spotify Connect Daemon")
        except Exception as exc:
            self.daemon_active = False
            log_msg("Cannot run SPOTTY: %s" % exc, xbmc.LOGNOTICE)


