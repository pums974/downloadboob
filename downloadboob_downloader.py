# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Tools used for downloadboob

    We will put here, functions directly relating to the search and download process
"""
__author__ = 'Alexandre Poux'

from io import open
import sys

from weboob.core import Weboob
from weboob.capabilities.video import CapVideo
from downloadboob_tools_weboob import *
from downloadboob_tools_kodi import *

DOWNLOAD_DIRECTORY = ".files"
links_directory = "Podcasts"
backend_directory = os.path.expanduser("~/.local/share/weboob/modules/1.0/")
kodi = True
down_live = False


def is_ok(video, title_regexp, id_regexp, author_regexp, title_exclude):
    """
        Test if the video is indeed what we are looking for
        :param title_regexp:
        :param id_regexp:
        :param author_regexp:
        :param title_exclude:
        :param video:
        :rtype : bool
    """
    if matched(video.title, title_regexp) is False:
        return False
    if matched(video.id, id_regexp) is False:
        return False
    if matched(video.author, author_regexp) is False:
        return False
    if matched(video.title, title_exclude):
        return False
    if matched(video.description, title_exclude):
        return False
    return True


class DownloadBoob(object):
    """
        Search and download
        :param name:
        :param backend_name:
        :param my_download_directory:
        :param my_links_directory:
    """

    def __init__(self, name, backend_name, my_download_directory,
                 my_links_directory):
        self.download_directory = my_download_directory
        self.links_directory = my_links_directory
        self.backend_name = backend_name
        self.backend = None
        self.weboob = Weboob()
        self.weboob.load_backends(modules=self.backend_name, )
        self.backend = self.weboob.get_backend(self.backend_name)
        self.name = name

    def get_filename(self, video, relative=False, m3u=False):
        """
            Generate filename for the video
            :param relative:
            :param m3u:
            :param video:
            :rtype : string
        """
        if relative:
            directory = os.path.join("..", DOWNLOAD_DIRECTORY,
                                     self.backend_name)
        else:
            directory = os.path.join(self.download_directory, self.backend_name)
            if not os.path.exists(directory):
                os.makedirs(directory)
        if not m3u:
            ext = video.ext
            if not ext:
                ext = 'avi'
        else:
            ext = 'm3u'
        return "%s/%s.%s" % (directory, removenonascii(video.id), ext)

    def get_linkname(self, video, m3u=False):
        """
            Generate filename for the link
            :param m3u:
            :param video:
            :rtype : string
        """
        if not os.path.exists(self.links_directory):
            os.makedirs(self.links_directory)
        if not m3u:
            ext = video.ext
            if not ext:
                ext = 'avi'
        else:
            ext = 'm3u'
        if not kodi:
            misc = video.date.strftime("%y-%m-%d")
            if not misc:
                misc = video.id
            return "%s/%s (%s).%s" % (self.links_directory,
                                      removespecial(video.title),
                                      removespecial(misc), ext)
        else:
            return "%s/%s.%s" % (self.links_directory,
                                 removespecial(video.title), ext)

    def is_downloaded(self, video):
        """
            Check if the video has already been downloaded
            :param video:
            :rtype : bool
        """
        if (os.path.isfile(self.get_filename(video)) or
            os.path.isfile(self.get_filename(video,
                                             m3u=True))):
            logging.info("%s Already downloaded : %s" %
                         (video.id, video.title))
            return True
        logging.debug("%s To be downloaded : %s" %
                      (video.id, video.title))
        return False

    def init_dir(self):
        """
            create directory
        """
        if not os.path.isdir(self.links_directory):
            logging.debug("  create link directory : %s" % self.links_directory)
            os.makedirs(self.links_directory)
        else:
            logging.debug("  existing link directory : %s" % self.links_directory)
        if kodi:
            file_name = os.path.join(self.links_directory, 'tvshow.nfo')
            show_name = self.links_directory.split("/")[-1]
            if not os.path.isfile(file_name):
                logging.debug("  create %s" % file_name)
                f = codecs.open(file_name, "w", "utf-8")
                f.write(u"<tvshow>\n")
                f.write(u"  <title>" + show_name + u"</title>\n")
                f.write(u"</tvshow>\n")
                f.close()
            else:
                logging.debug("  existing %s" % file_name)

    def do_search(self,
                  pattern=None,
                  pattern_type="search",
                  sortby=CapVideo.SEARCH_RELEVANCE,
                  nsfw=False):
        """
            Search for videos
            :param pattern:
            :param pattern_type:
            :param sortby:
            :param nsfw:
            :return:
        """
        logging.debug("  Searching for videos for %s" % self.name)
        list_videos = []
        if pattern_type == "search":
            list_videos = self.backend.search_videos(pattern, sortby, nsfw)
        elif pattern_type == "ls":
            sys.path.insert(
                0, backend_directory + "/" + self.backend.name + "/"
            )  # HACK
            if 'video' in sys.modules:
                del sys.modules['video']
            if self.backend.name == "arte":
                from video import ArteVideo as Video_Init
            elif self.backend.name == "canalplus":
                from video import CanalplusVideo as Video_Init
            elif self.backend.name == "arretsurimages":
                from video import ArretSurImagesVideo as Video_Init
            elif self.backend.name == "dailymotion":
                from video import DailymotionVideo as Video_Init
            elif self.backend.name == "nolifetv":
                from video import NolifeTVVideo as Video_Init
            elif self.backend.name == "youtube":
                from video import YoutubeVideo as Video_Init
            else:
                from weboob.capabilities.video import BaseVideo as Video_Init  # END OF HACK
            for videoid in videoob_list_rep(pattern, self.backend):
                list_videos.append(Video_Init(videoid))
        if list_videos:
            logging.debug("  found videos for %s" % self.name)
        else:
            logging.error("  did not found videos for %s" % self.name)
        return list_videos

    def filter_list(self, list_videos, title_regexp, id_regexp, author_regexp,
                    title_exclude, max_results):
        """
            Filter the list after the search
            :param list_videos:
            :param title_regexp:
            :param id_regexp:
            :param author_regexp:
            :param title_exclude:
            :param max_results:
            :return:
        """
        logging.debug("  filtering list of found video for %s" % self.name)
        videos = []
        num_videos = 0
        for video in list_videos:
            if is_ok(video, title_regexp, id_regexp, author_regexp,
                     title_exclude):
                if not self.is_downloaded(video):
                    videoob_get_info(self.backend, video)
                    if not video:
                        logging.error('Error in Video: %s' % video)
                    elif not video.url:
                        logging.error(
                            'Error: the URL is not available : %s (%s)' %
                            (video.url, video.id))
                    else:
                        if is_ok(video, title_regexp, id_regexp, author_regexp,
                                 title_exclude):
                            num_videos += 1
                            if not self.is_downloaded(video):
                                videos.append(video)
                                print("New Video :  %s" % video.title)
                                print("    Description:%s" % video.description)
                                print("    Author:%s" % video.author)
                                print("    Id:%s" % video.id)
                                print("    Duration:%s" % video.duration)
                                print("    Date:%s" % video.date)
                            if num_videos == max_results:
                                break
        return videos

    def write_m3u(self, video):
        """
            Write m3u file for streaming files
            :param video:
            :return:
        """
        logging.debug("  Write m3u for %s" % video.title)
        if video.ext == "m3u" or video.ext == "m3u8":
            return do_download(video, self.get_filename(video))
        else:
            if matched(video.url, "\.m3u") or matched(video.url, "\.m3u8"):
                return do_download(video, self.get_filename(video))
            else:
                dest = self.get_filename(video, m3u=True)
                show_name = self.links_directory.split("/")[-1]
                logging.debug("  create %s" % dest)
                f = codecs.open(dest, "w", "utf-8")
                f.write("#EXTINF: ")
                if video.duration:
                    f.write(str(video.duration))
                else:
                    f.write(str(-1))
                f.write(", " + show_name + " - " + video.title + "\n")
                f.write(video.url)
                f.close()
                return 0

    def set_link(self, video, m3u=False):
        """
            Create link file
            :param video:
            :param m3u:
        """
        linkname = self.get_linkname(video, m3u=m3u)
        idname = self.get_filename(video, relative=True, m3u=m3u)
        absolute_idname = self.get_filename(video, m3u=m3u)
        if not os.path.islink(linkname) and os.path.isfile(absolute_idname):
            logging.info("  %s -> %s" % (linkname, idname))
            os.symlink(idname, linkname)
        else:
            logging.debug("  Not generating link for %s" % video.title)

    def do_mv(self, video, m3u=False):
        """
            move video file after download
            :param video:
            :param m3u:
        """
        linkname = self.get_linkname(video, m3u=m3u)
        absolute_idname = self.get_filename(video, m3u=m3u)
        if not os.path.isfile(linkname) and os.path.isfile(absolute_idname):
            logging.info("  %s => %s" % (absolute_idname, linkname))
            os.rename(absolute_idname, linkname)
            open(absolute_idname, 'w').close()
        else:
            logging.debug("  Not moving file %s" % linkname)

    def download(self,
                 pattern=None,
                 sortby=CapVideo.SEARCH_RELEVANCE,
                 nsfw=False,
                 max_results=20,
                 title_regexp=None,
                 id_regexp=None,
                 pattern_type="search",
                 author_regexp=None,
                 title_exclude=None):
        # create directory for links
        """
            Main process
            :param pattern:
            :param sortby:
            :param nsfw:
            :param max_results:
            :param title_regexp:
            :param id_regexp:
            :param pattern_type:
            :param author_regexp:
            :param title_exclude:
        """
        self.init_dir()

        # search for videos
        list_videos = self.do_search(pattern, pattern_type, sortby, nsfw)

        # Filter the list of videos
        videos = self.filter_list(list_videos, title_regexp, id_regexp,
                                  author_regexp, title_exclude, max_results)

        # download videos
        if videos:
            for video in videos:
                print("Downloading... " + video.title)
                if kodi:  # THE "TITLE" BECOME "S00E00 - TITLE (ID)"
                    rewrite_title(video)
                if down_live:  # CREATE LIVE STREAM
                    ret = self.write_m3u(video)
                else:  # DOWNLOAD VIDEO
                    ret = do_download(video, self.get_filename(video)
                                      )  # FOR DIRECT LINKS
                    if not ret:
                        ret = do_conv(video, self.get_filename(video)
                                      )  # FOR INDIRECT LINKS
                if not ret:
                    if not kodi:
                        self.set_link(
                            video
                        )  # CREATE LINKS FOR A BEAUTIFULL LIBRARY
                    else:
                        self.do_mv(video)  # MOVE FILES FOR A BEAUTIFULL LIBRARY
                        # CREATE NFO FILES FOR KODI
                        write_nfo(self.get_linkname(video),
                                  self.links_directory, self.backend_name,
                                  video)
                    print("Downloaded : " + video.title)
                else:
                    assert isinstance(video.title, basestring)
                    print("Failed download :" + video.title)
