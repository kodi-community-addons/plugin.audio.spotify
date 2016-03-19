'''
Copyright 2011 Mikel Azkolain

This file is part of Spotify.

Spotify is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotify is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotify.  If not, see <http://www.gnu.org/licenses/>.
'''



import logging, xbmc


_trans_table = {
    logging.DEBUG: xbmc.LOGDEBUG,
    logging.INFO: xbmc.LOGINFO,
    logging.WARNING: xbmc.LOGWARNING,
    logging.ERROR: xbmc.LOGERROR,
    logging.CRITICAL: xbmc.LOGSEVERE,
}


class XbmcHandler(logging.Handler):
    def emit(self, record):
        xbmc_level = _trans_table[record.levelno]
        xbmc.log(record.msg, xbmc_level)



def setup_logging():
    handler = XbmcHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)



def get_logger():
    return logging.getLogger('Spotify')
