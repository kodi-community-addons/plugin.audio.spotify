#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
    script.module.metadatautils
    extraposter.py
    Get extraposter location for kodi media
"""

import os
import xbmcvfs


def get_extraposter(file_path):
    """get extraposter path on disk based on media path"""
    result = {}
    efa_path = ""
    if "plugin.video.emby" in file_path:
        # workaround for emby addon
        efa_path = u"plugin://plugin.video.emby/extraposter?path=" + file_path
    elif "plugin://" in file_path:
        efa_path = ""
    elif "videodb://" in file_path:
        efa_path = ""
    else:
        count = 0
        while not count == 3:
            # lookup extraposter folder by navigating up the tree
            file_path = os.path.dirname(file_path)
            try_path = file_path + u"/extraposter/"
            if xbmcvfs.exists(try_path):
                efa_path = try_path
                break
            count += 1

    if efa_path:
        result["art"] = {"extraposter": efa_path}
        for count, file in enumerate(xbmcvfs.listdir(efa_path)[1]):
            if file.lower().endswith(".jpg"):
                if sys.version_info.major == 3:
                    result["art"]["ExtraPoster.%s" % count] = efa_path + file
                else:
                    result["art"]["ExtraPoster.%s" % count] = efa_path + file.decode("utf-8")
    return result
