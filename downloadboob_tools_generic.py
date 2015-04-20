# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Tools used for downloadboob

    We will put here, simple functions that are not relating to weboob or kodi
"""

from __future__ import print_function
from __future__ import unicode_literals

__author__ = 'Alexandre Poux'

import re
from subprocess import Popen, CalledProcessError, PIPE
import logging
import os


rx = re.compile('[ \\/\\?\\:\\>\\<\\!\\\\\\*]+', re.UNICODE)
exec_wget = ""
exec_curl = ""
exec_avconv = ""
exec_ffmpeg = ""
exec_rtmpdump = ""
exec_mimms = ""


def init_tools():
    """
        Find tools that will be usefull
    """
    global exec_wget
    global exec_curl
    global exec_avconv
    global exec_ffmpeg
    global exec_rtmpdump
    global exec_mimms

    # Check availability of dependencies
    exec_wget = check_exec('wget')
    exec_curl = check_exec('curl')
    exec_avconv = check_exec('avconv')
    exec_ffmpeg = check_exec('ffmpeg')
    exec_rtmpdump = check_exec('rtmpdump')
    exec_mimms = check_exec('mimms')


def removenonascii(s):
    """
        Remove non ASCII character from a string
        :rtype : basestring
        :param s:
        :return:
    """
    return "".join(char for char in s if ord(char) < 128)


def removespecial(s):
    """
        Remove non ASCII character from a string
        :rtype : basestring
        :param s:
        :return:
    """
    return rx.sub(' ', '%s' % s)


def matched(string, regexp):
    """
        Check if a string satisfy a regexp
        :rtype : logical
        :param string:
        :param regexp:
        :return:
    """
    if regexp and string and not string == "Not loaded":
        return re.search(regexp, string) is not None
    return None


def check_exec(executable):
    """
        Check if the executable exist
        :rtype : path
        :param executable:
        :return:
    """
    try:
        output, error = Popen(['which', executable],
                              stdout=PIPE,
                              stderr=PIPE).communicate()
        if not error:
            logging.info('Path to %s : %s' % (executable, output.replace("\n", "")))
            return output
    except CalledProcessError:
        logging.info('error with which !?!?' % executable)
        return ""
    logging.info('%s Not found' % executable)
    return ""


def check_link(links_directory, link_name):
    """
        Check existence of the linkfile's target
        :rtype : bool
        :param links_directory:
        :param link_name:
    """
    if os.path.islink(link_name):
        file_name = os.readlink(link_name)
        absolute_file_name = os.path.join(links_directory, file_name)
        if os.path.isfile(absolute_file_name):
            logging.debug("Link still valid : %s -> %s" % (link_name, absolute_file_name))
            return True
        return False
    else:
        return True


def purge(links_directory):
    """
        remove link if target have been removed
        :param links_directory:
    """
    if not os.path.isdir(links_directory):
        return
    logging.debug("Purging %s" % links_directory)
    dirlist = os.listdir(links_directory)
    for local_link_name in dirlist:
        link_name = links_directory + "/" + local_link_name
        if not check_link(links_directory, link_name):
            logging.info("Removing %s" % link_name)
            os.remove(link_name)


def do_download(video, filename):
    """
        Download video file
        :param video:
        :param filename:
        :return:
    """
    if video.url.startswith('rtmp'):
        if not exec_rtmpdump:
            logging.error('I Need rtmpdump')
            return 1
        args = ['rtmpdump', '-e', '-r', video.url, '-o', filename]
    elif video.url.startswith('mms'):
        if not exec_mimms:
            logging.error('I Need mimms')
            return 1
        args = ['mimms', video.url, filename]
    else:
        if not exec_wget:
            if not exec_curl:
                logging.error('I Need curl or wget')
                return 1
            else:
                args = ['curl', '-s', video.url, '-o', filename]
        else:
            args = ['wget', '-q', video.url, '-O', filename]
    logging.debug("downloading %s with %s" % (video.title, args[0]))
    process = Popen(args, stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    res = process.wait()
    logging.info(output)
    if error:
        logging.error(error)
    return res


def do_conv(video, filename):
    """
        Convert a streaming file into a video file
        :param video:
        :param filename:
    """
    if video.ext == "m3u" or video.ext == "m3u8":
        video.ext = 'avi'
        if not exec_avconv:
            if not exec_ffmpeg:
                logging.error('I Need avconv or ffmpeg')
                return 1
            else:
                args = ['ffmpeg', '-i', video.url, '-vcodec', 'copy',
                        '-acodec', 'copy', '-loglevel', 'error',
                        filename]  # "-stat" ,'-threads', '8'
        else:
            args = ['avconv', '-i', video.url, '-c', 'copy', filename]
        logging.debug("Converting %s with %s" % (video.title, args[0]))
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
        res = process.wait()
        logging.info(output)
        if error:
            logging.debug(error)
        return res
    else:
        logging.debug("Not Converting %s, i don't understand" % video.title)
        return 0


def init_logging():
    """
        Define the logging file
        It's possible to set the level to logging.DEBUG if you want more verbosity
    """
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
                        datefmt='%m-%d %H:%M',
                        filename='downloadboob.log')

    # Also log on the console
    # it's possible to set the level to logging.DEBUG if you want more verbosity
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logformatter = logging.Formatter("%(message)s")
    console.setFormatter(logformatter)
    logging.getLogger('').addHandler(console)
    logging.warning("Hello")