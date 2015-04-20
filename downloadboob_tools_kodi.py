# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Tools used for downloadboob

    We will put here, functions directly relating to weboob
"""
__author__ = 'Alexandre Poux'
from downloadboob_tools_generic import *


def rewrite_title(video):
    """
        Rename the title for KODI compatibility
        :param video:
    """
    video.title = "S00E00 - " + video.title + " (" + str(video.id) + ")"
    return True


def write_nfo(linkname, links_directory, backend_name, video):
    """
        Write nfo file for KODI
        :param links_directory:
        :param backend_name:
        :param linkname:
        :param video:
    """
    nfoname, _ = os.path.splitext(linkname)
    nfoname += ".nfo"
    if not os.path.isfile(nfoname):
        logging.debug('writing nfo for video : %s' % video.title)
        show_name = links_directory.split("/")[-1]
        logging.info("  create %s" % nfoname)
        f = open(nfoname, 'w')
        f.write("<episodedetails>\n")
        f.write("  <title>" + video.title + "</title>\n")
        f.write("  <showtitle>" + show_name + "</showtitle>\n")
        f.write("  <season>0</season>\n")
        f.write("  <episode>0</episode>\n")
        if video.date:
            f.write("  <aired>" + video.date.isoformat() + "</aired>\n")
        if video.duration:
            f.write("  <runtime>" + str(int(video.duration.total_seconds() /
                                            60)) + "</runtime>\n")
        if video.author:
            f.write("  <studio>" + video.author + "</studio>\n")
        else:
            f.write("  <studio>" + backend_name + "</studio>\n")
        if video.description:
            f.write("  <plot>" + video.description + "</plot>\n")
        f.write("  <displayseason />\n")
        f.write("  <displayepisode />\n")
        f.write("</episodedetails>\n")
        f.close()
        return True
    else:
        logging.debug('nfo already present for video %s' % video.title)
        return False
