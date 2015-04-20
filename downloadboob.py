# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Downloader for Weboob, usable in cron
"""
# Copyright(C) 2012 Alexandre Flament
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

__author__ = 'Alexandre Poux'

import ConfigParser
from multiprocessing import Process, Queue, cpu_count
from Queue import Empty
from traceback import format_exc

from downloadboob_downloader import *

# hack to workaround bash redirection and encoding problem
import codecs
import locale

#if sys.stdout.encoding is None:
#    (lang, enc) = locale.getdefaultlocale()
#    if enc is not None:
#        (e, d, sr, sw) = codecs.lookup(enc)
#        # sw will encode Unicode data to the locale-specific character set.
#        sys.stdout = sw(sys.stdout)
## end of hack


def init_config(configfile):
    """
        Initial reading of the config file
        :param configfile:
    """
    global links_directory
    global down_live
    global kodi
    global backend_directory
    global download_directory
    configfile.read(['/etc/downloadboob.conf',
                     #os.path.expanduser('~/downloadboob.conf'),
                     'downloadboob.conf'])
    try:
        links_directory = os.path.expanduser(
            configfile.get('main', 'directory', '.').decode('utf8'))
    except ConfigParser.NoSectionError:
        print(
            "Please create a configuration file (see the README file and the downloadboob.conf example file)")
        exit(2)

    if configfile.has_option("main", "live"):
        down_live = configfile.getboolean("main", "live")

    if configfile.has_option("main", "kodi"):
        kodi = configfile.getboolean("main", "kodi")

    if configfile.has_option("main", "backend_directory"):
        backend_directory = os.path.expanduser(
            configfile.get("main", "backend_directory").decode('utf8'))

    download_directory = os.path.join(links_directory, DOWNLOAD_DIRECTORY)

    print("Downloading to %s" % links_directory)


def read_config(configfile, my_section):
    """
        Reading the config file
        :param configfile:
        :param my_section:
    """
    backend_name = configfile.get(my_section, "backend").decode('utf8')
    if check_backend(backend_name):
        pattern = configfile.get(my_section, "pattern").decode('utf8')
        section_sublinks_directory = configfile.get(my_section,
                                                    "directory").decode('utf8')
        if configfile.has_option(my_section, "type"):
            pattern_type = configfile.get(my_section, "type").decode('utf8')
        else:
            pattern_type = "search"
        if configfile.has_option(my_section, "title_regexp"):
            title_regexp = configfile.get(my_section,
                                          "title_regexp").decode('utf8')
        else:
            title_regexp = None
        if configfile.has_option(my_section, "title_exclude"):
            title_exclude = configfile.get(my_section,
                                           "title_exclude").decode('utf8')
        else:
            title_exclude = None
        if configfile.has_option(my_section, "id_regexp"):
            id_regexp = configfile.get(my_section, "id_regexp").decode('utf8')
        else:
            id_regexp = None
        if configfile.has_option(my_section, "author_regexp"):
            author_regexp = configfile.get(my_section,
                                           "author_regexp").decode('utf8')
        else:
            author_regexp = None
        if configfile.has_option(my_section, "max_results"):
            max_result = configfile.getint(my_section, "max_results")
        else:
            max_result = 50
        section_links_directory = os.path.join(links_directory,
                                               section_sublinks_directory)
        # if not backend_name == "youtube":

        # Initialize and do some cleaning
        downloadboob = DownloadBoob(my_section, backend_name,
                                    download_directory,
                                    section_links_directory)
        purge(downloadboob.links_directory)

        # Search and download
        logging.info("For backend %s, start search for '%s'" %
                     (backend_name, my_section))
        downloadboob.download(pattern=pattern, sortby=CapVideo.SEARCH_DATE, max_results=max_result,
                              title_regexp=title_regexp, id_regexp=id_regexp, pattern_type=pattern_type,
                              author_regexp=author_regexp, title_exclude=title_exclude)
        # Repeat, because the SEARCH_RELEVANCE may give better results than SEARCH_DATE
        if pattern_type == "search":  # FIXME (AT LEAST) FOR YOUTUBE
            logging.info("For backend %s, start search-bis for '%s'" %
                         (backend_name, my_section))
            downloadboob.download(pattern=pattern, max_results=max_result, title_regexp=title_regexp,
                                  id_regexp=id_regexp, pattern_type=pattern_type, author_regexp=author_regexp,
                                  title_exclude=title_exclude)
        print("For backend %s, end search for '%s'" %
              (backend_name, my_section))


def do_work(q):
    """
        What a process have to do
        :param q:
    """
    try:
        while True:
            try:
                # Is there any work to do ?
                my_section = q.get(block=False)
            except Empty:
                # Nothing to do, kill myself
                if q.empty():
                    break
            else:
                # Extract details of my work from config file
                read_config(config, my_section)
    except KeyboardInterrupt:
        print("Shutdown requested...exiting")
        exit(0)
    except Exception:
        print("Something wrong happend")
        stk = format_exc()
        logging.debug(stk)
        exit(3)


init_logging()
init_tools()
exec_videoob = check_exec('videoob')

# Crash if we don't find videoob
if not exec_videoob:
    print('I need videoob !')
    exit(1)

# Due to frequent updates to websites
# Update the backends
logging.info("Backends update")
out, err = Popen(["weboob-config", "update"],
                 stdout=PIPE,
                 stderr=PIPE).communicate()
logging.info(out)
if err:
    logging.error(err)

config = ConfigParser.ConfigParser()
init_config(config)

# Count the number of process we have at our disposal
nproc = cpu_count()

if __name__ == '__main__':
    # Each section of the config file is a Task to be done by one process or an another
    # Build a queue with those tasks
    work_queue = Queue()
    res_queue = Queue()
    for section in config.sections():
        if section != "main":
            work_queue.put(section)
    nproc_ = [Process(target=do_work,
                      args=(work_queue, )) for i in range(nproc)]
    processes = nproc_
    # Let's work
    for p in processes:
        p.start()
    # Wait for the work to be done
    for p in processes:
        p.join()

# The end, everything happened normally
exit(0)
