#!/usr/bin/env python2
# -*- coding: utf8 -*-

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

from __future__ import print_function
from __future__ import unicode_literals

import os
from io import open
from traceback import print_tb

import ConfigParser

import re
from datetime import datetime,timedelta

from weboob.core import Weboob
from weboob.capabilities.base import NotLoadedType
from weboob.capabilities.video import CapVideo,BaseVideo

from subprocess import Popen, check_output,call,CalledProcessError
from multiprocessing import Pool,Process,cpu_count,Queue
from Queue import Empty

# hack to workaround bash redirection and encoding problem
import sys
import codecs
import locale

if sys.stdout.encoding is None:
    (lang, enc) = locale.getdefaultlocale()
    if enc is not None:
        (e, d, sr, sw) = codecs.lookup(enc)
        # sw will encode Unicode data to the locale-specific character set.
        sys.stdout = sw(sys.stdout)
# end of hack

def removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

rx = re.compile('[ \\/\\?\\:\\>\\<\\!\\\\\\*]+', re.UNICODE)

def removeSpecial(s):
    return rx.sub(' ', '%s' % s)

def check_backend(backend_name):
    # Check if the backend is installed
    output = check_output(['videoob', "backend","list"],stderr=stderr, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8')
    list_backend = output.splitlines()[0].split(": ")[1].split(", ")
    if backend_name in list_backend:
        print('Backend %s found' %  backend_name, file=stdout)
        return True
    else:
        print('Backend %s not found' %  backend_name, file=stdout)
        # Check if the backend is installable
        output = check_output(["videoob","backend","list-modules"],stderr=stderr, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8')
        list_backend=[]
        for line in output.splitlines():
          if not matched(line,"^Modules list:"):
            list_backend.append(line.split("] ")[1].split(" ")[0])
        if backend_name in list_backend:
            print('Installing backend %s' %  backend_name)
            return call(["videoob","backend","add",backend_name],stderr=stderr) == 0
        else:
            print('Backend %s unknown' %  backend_name, file=stdout)
            return False

def check_exec(executable):
    print('Looking for which %s to use : ' %  executable, file=stdout, end="")
    try:
        output = check_output(['which', executable],stderr=stderr2).decode('utf8')
    except CalledProcessError:
        print('None', file=stdout)
        return ""
    else:
        print('%s' %  output, file=stdout)
        return output


def matched(string, regexp):
    if regexp and string:
        return re.search(regexp, string) is not None
    return None


def check_link(link_name,links_directory):
    if os.path.islink(link_name):
        file_name = os.readlink(link_name)
        absolute_file_name = os.path.join(links_directory, file_name)
        if os.path.isfile(absolute_file_name):
            return True
        return False
    else:
        return True

def purge(links_directory):
    #remove link if target have been removed
    if not os.path.isdir(links_directory):
        return
    dirList=os.listdir(links_directory)
    for local_link_name in dirList:
        link_name = links_directory + "/" + local_link_name
        if not check_link(link_name,links_directory):
            print("Remove %s" % link_name,file=stdout)
            os.remove(link_name)

def convert_videos(old_videos):
    new_videos=[]
    new_video=Generic_video()
    for old_video in old_videos:
        new_video.title = old_video.title
        new_video.url = old_video.url
        new_video.ext = old_video.ext
        new_video.duration = old_video.duration
        new_video.author = old_video.author
        new_video.date = old_video.date
        new_video.description = old_video.description
        new_video.id = old_video.id

        new_videos.append(new_video)
    return new_videos
   

class Specific_video(object):
    from weboob.capabilities.video import BaseVideo as video_init
    def __init__(self, backend_name):
          sys.path.insert(0,backend_directory+"/"+backend_name+"/" ) # HACK
          if 'video' in sys.modules:
             del sys.modules['video']
          if backend_name == "arte":
             from video import ArteVideo as video_init
          elif backend_name == "canalplus":
             from video import CanalplusVideo as video_init
          elif backend_name == "arretsurimages":
             from video import ArretSurImagesVideo as video_init
          elif backend_name == "dailymotion":
             from video import DailymotionVideo as video_init
          elif backend_name == "nolifetv":
             from video import NolifeTVVideo as video_init
          elif backend_name == "youtube":
             from video import YoutubeVideo as video_init

class Generic_video(object):
    def __init__(self):
        self.id = ""
        self.title = ""
        self.url = ""
        self.ext = ""
        self.duration = timedelta()
        self.author = ""
        self.date = datetime.now()
        self.description = ""


class Searchboob(object):

    def __init__(self, backend_name, download_directory,criteria,links_directory):
        self.backend_name = backend_name
        self.download_directory = download_directory
        self.links_directory=links_directory
        self.criteria=criteria


    def is_downloaded(self, video):
        if os.path.isfile(self.get_filename(video)) or os.path.isfile(self.get_filename(video,m3u=True)):
           print("%s Already downloaded : %s" % (video.id,video.title), file=stdout)
           return True
        else:
           return False

    def is_ok(self,video,title_regexp,id_regexp,author_regexp,title_exclude):
        if matched(video.title,title_regexp) == False:
            return False
        if matched(video.id,id_regexp) == False:
            return False
        if matched(video.author,author_regexp) == False:
            return False
        if matched(video.title,title_exclude) == True:
            return False
        if matched(video.description,title_exclude) == True:
            return False
        return True

    def get_filename(self, video, relative=False,m3u=False):
        if relative:
            directory = os.path.join("..", DOWNLOAD_DIRECTORY, self.backend_name)
        else:
            directory = os.path.join(self.download_directory, self.backend_name)
            if not os.path.exists(directory):
                os.makedirs(directory)
        if not m3u:
          ext = video.ext
          if not ext:
              ext = 'avi'
        else:
          ext='m3u'
        return "%s/%s.%s" % (directory, removeNonAscii(video.id), ext)

    def videoob_list_rep(self,rep,backend):
        list_id=[]
        list_rep=list(backend.iter_resources((BaseVideo,), rep.split("/") ))
        for fich in list_rep:
            if fich.id:
               list_id.append(fich.id)
            else:
               list_id.append(self.videoob_list_rep(rep+"/"+fich.title,self.backend_name))
        return sorted(set(list_id))

    def do_search(self, pattern=None,pattern_type="search", sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        weboob=Weboob()
        weboob.load_backends(modules=[self.backend_name])
        backend=weboob.get_backend(self.backend_name)
        list_videos=[]
        if pattern_type == "search":
            list_videos=backend.search_videos(pattern, sortby, nsfw)
        elif pattern_type == "ls":
            for id in self.videoob_list_rep(pattern,backend):
                video=Specific_video(self.backend_name).video_init(id)
                list_videos.append(video)
        return list_videos

    def videoob_get_info(self,video): # THIS IS COSTLY
        try: 
            output = check_output(['videoob', "info","--backend="+self.backend_name,"--",video.id],stderr=stderr, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8') 
        except CalledProcessError as test1:
            if video.title :
                print("videoob info for %s failed : \n%s : %s" % (video.id+" - "+video.title,type(test1).__name__,test1 ) ,file=stderr)
            else:
                print("videoob info for %s failed : \n%s : %s" % (video.id,type(test1).__name__,test1 ) ,file=stderr)
            weboob=Weboob()
            weboob.load_backends(modules=[backend_name])
            backend=weboob.get_backend(backend_name)
            try:
                backend.fill_video(video, ('ext','title', 'url', 'duration', 'author', 'date', 'description')) # This is incomplete for some backends
            except Exception as test2:
                if video.title :
                    print("Impossible to find info about the video %s :\n%s : %s" % (video.id+" - "+video.title,type(test2).__name__,test2 ) ,file=stderr)
                else:
                    print("Impossible to find info about the video %s :\n%s : %s" % (video.id,type(test2).__name__,test2) ,file=stderr)
        else:
            for line in output.splitlines():
                prefix=line.split(": ")[0]
                suffix=line[len(prefix)+2:]
                if prefix == "ext":
                    video.ext=suffix
                elif prefix == "title":
                    video.title=suffix
                elif prefix == "description":
                    video.description=suffix
                elif prefix == "url":
                    video.url=suffix
                elif prefix == "author":
                    video.author=suffix
                elif prefix == "duration":
                    t=datetime.strptime(suffix,"%H:%M:%S")
                    video.duration=timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                elif prefix == "date" and suffix:
                    video.date=datetime.strptime(suffix[0:19],"%Y-%m-%d %H:%M:%S")

    def filter_list(self,list_videos,title_regexp,id_regexp,author_regexp,title_exclude,max_results):
        videos = []
        i=0
        for video in list_videos:
            if self.is_ok(video,title_regexp,id_regexp,author_regexp,title_exclude):
                if not self.is_downloaded(video):
                  self.videoob_get_info(video)
                  if not video:
                      print('Video not found: %s' %  video, file=stderr)
                  elif not video.url:
                      print('Error: the URL is not available : %s (%s)' % (video.url,video.id), file=stderr)
                  else:
                      if self.is_ok(video,title_regexp,id_regexp,author_regexp,title_exclude):
                        i+=1
                        if not self.is_downloaded(video):
                            videos.append(video)
                            print("New Vidéo :  %s\n    Description:%s\n    Author:%s\n    Id:%s\n    Duration:%s\n    Date:%s" 
                                          % (video.title,video.description,video.author, video.id, video.duration, video.date), file=stdout)
                        if i == max_results:
                            break
        return videos


    def search(self):

        print("For backend %s, start search for '%s'" % (self.backend_name,self.criteria.pattern),file=stdout)
        # search for videos
        list_videos=self.do_search(self.criteria.pattern,
                                   self.criteria.pattern_type,
                                   self.criteria.sortby,
                                   self.criteria.nsfw)

        # convert specific type in generic type
        list_videos=convert_videos(list_videos)

        # Filter the list of videos
        return self.filter_list(list_videos,self.criteria.title_regexp,
                                            self.criteria.id_regexp,
                                            self.criteria.author_regexp,
                                            self.criteria.title_exclude,
                                            self.criteria.max_results)


class Downloadboob(object):

    def __init__(self, video,backend_name, download_directory, links_directory):
        self.backend_name = backend_name
        self.download_directory = download_directory
        self.links_directory = links_directory
        self.video=video

    def get_filename(self, relative=False,m3u=False):
        if relative:
            directory = os.path.join("..", DOWNLOAD_DIRECTORY, self.backend_name)
        else:
            directory = os.path.join(self.download_directory, self.backend_name)
            if not os.path.exists(directory):
                os.makedirs(directory)
        if not m3u:
          ext = self.video.ext
          if not ext:
              ext = 'avi'
        else:
          ext='m3u'
        return "%s/%s.%s" % (directory, removeNonAscii(self.video.id), ext)

    def get_linkname(self, m3u=False):
        if not os.path.exists(self.links_directory):
            os.makedirs(self.links_directory)
        if not m3u:
          ext = self.video.ext
          if not ext:
              ext = 'avi'
        else:
          ext='m3u'
        if not kodi:
            misc = self.video.date.strftime("%y-%m-%d")
            if not misc:
                misc = self.video.id
            return "%s/%s (%s).%s" % (self.links_directory, removeSpecial(self.video.title), removeSpecial(misc), ext)
        else:
            return "%s/%s.%s" % (self.links_directory, removeSpecial(self.video.title), ext)

    def rewrite_title(self): #FOR KODI
        self.video.title = "S00E00 - "+self.video.title+" ("+str(self.video.id)+")"

    def init_dir(self):
        # create directory
        if not os.path.isdir(self.links_directory):
            print("  create link directory : %s" % self.links_directory,file=stdout)
            os.makedirs(self.links_directory)
        if kodi:
            file_name = os.path.join(self.links_directory, 'tvshow.nfo')
            Show_name = self.links_directory.split("/")[-1]
            if not os.path.isfile(file_name):
                print("  create %s" % file_name,file=stdout)
                f=open(file_name,'w')
                f.write("<tvshow>\n")
                f.write("  <title>"+Show_name+"</title>\n")
                f.write("</tvshow>\n")
                f.close()

    def write_m3u(self):
        if self.video.ext == "m3u" or self.video.ext == "m3u8":
            return self.do_download(conv=False)
        else:
            if matched(self.video.url,"\.m3u") or matched(self.video.url,"\.m3u8"):
                return self.do_download(conv=False)
            else:
                dest = self.get_filename(m3u=True)
                Show_name = self.links_directory.split("/")[-1]
                print("  create %s" % dest, file=stdout)
                f=open(dest, 'w')
                f.write("#EXTINF: ")
                if self.video.duration:
                   f.write(str(self.video.duration))
                else:
                   f.write(str(-1))
                f.write(", "+Show_name+" - "+self.video.title+"\n")
                f.write(self.video.url) 
                f.close()
                return 0

    def do_download(self):
        dest = self.get_filename()
        if self.video.url.startswith('rtmp'):
            if not exec_rtmpdump:
                print('I Need rtmpdump', file=stderr)
                return 1
            args = ['rtmpdump', '-e', '-r', self.video.url, '-o', dest]
        elif self.video.url.startswith('mms'):
            if not exec_mimms:
                print('I Need mimms', file=stderr)
                return 1
            args = ['mimms', self.video.url, dest]
        else:
            if not exec_wget:
                if not exec_curl:
                    print('I Need curl or wget', file=stderr)
                    return 1
                else:
                    args = ['curl','-s', self.video.url, '-o', dest]
            else:
                args = ['wget','-q', self.video.url, '-O', dest]
        return call(args,stderr=stderr,stdout=stdout)

    def do_conv(self):
        dest = self.get_filename()
        if  self.video.ext == "m3u" or self.video.ext == "m3u8":
           self.video.ext='avi'
           dest = self.get_filename()
           if not exec_avconv:
              if not exec_ffmpeg:
                 print('I Need avconv or ffmpeg', file=stderr)
                 return 1
              else:
                 args = ['ffmpeg','-i', self.video.url, '-vcodec','copy','-acodec','copy','-loglevel','error', dest] #"-stat" ,'-threads', '8'
           else:
              args = ['avconv','-i', self.video.url, '-c','copy', dest]
           return call(args,stderr=stderr,stdout=stdout)
        else:
           return 0

    def set_link(self, m3u=False):
        linkname = self.get_linkname(m3u=m3u)
        idname = self.get_filename( relative=True,m3u=m3u)
        absolute_idname = self.get_filename( relative=False,m3u=m3u)
        if not os.path.islink(linkname) and os.path.isfile(absolute_idname):
            print("  %s -> %s" % (linkname, idname), file=stdout)
            os.symlink(idname, linkname)

    def do_mv(self, m3u=False):
        linkname = self.get_linkname(m3u=m3u)
        idname = self.get_filename( relative=True,m3u=m3u)
        absolute_idname = self.get_filename( relative=False,m3u=m3u)
        if not os.path.isfile(linkname) and os.path.isfile(absolute_idname):
            print("  %s => %s" % (absolute_idname,linkname), file=stdout)
            os.rename(absolute_idname, linkname)
            open(absolute_idname, 'w').close() 

    def write_nfo(self):
        nfoname, _ = os.path.splitext(self.get_linkname())
        nfoname = nfoname+".nfo"
        if not os.path.isfile(nfoname):
            Show_name = self.links_directory.split("/")[-1]
            print("  create %s" % nfoname, file=stdout)
            f=open(nfoname,'w')
            f.write("<episodedetails>\n")
            f.write("  <title>"+self.video.title+"</title>\n")
            f.write("  <showtitle>"+Show_name+"</showtitle>\n")
            f.write("  <season>0</season>\n")
            f.write("  <episode>0</episode>\n")
            if self.video.date:
                  f.write("  <aired>"+self.video.date.isoformat()+"</aired>\n")
            if self.video.duration:
                  f.write("  <runtime>"+str(int(self.video.duration.total_seconds()/60))+"</runtime>\n")
            if self.video.author:
                  f.write("  <studio>"+self.video.author+"</studio>\n")
            else:
                  f.write("  <studio>"+self.backend_name+"</studio>\n")
            if self.video.description:
                  f.write("  <plot>"+self.video.description+"</plot>\n")
            f.write("  <displayseason />\n")
            f.write("  <displayepisode />\n")
            f.write("</episodedetails>\n")
            f.close()

    def download(self):
        # create directory for links
        self.init_dir()

        # download a video
        print("Downloading... "+self.video.title)
        if kodi:                           # THE "TITLE" BECOME "S00E00 - TITLE (ID)"
            self.rewrite_title()
        if down_live:                      # CREATE LIVE STREAM
            ret=self.write_m3u()
        else:                              # DOWNLOAD VIDEO
            ret=self.do_download()           # FOR DIRECT LINKS
            if not ret: ret=self.do_conv()   # FOR INDIRECT LINKS
        if not ret:
            if not kodi:
                self.set_link()        # CREATE LINKS FOR A BEAUTIFULL LIBRARY
            else:
                self.do_mv()           # MOVE FILES FOR A BEAUTIFULL LIBRARY
                self.write_nfo()       # CREATE NFO FILES FOR KODI
            print("Downloaded : "+self.video.title)
        else:
            print("Failed download :"+self.video.title)

class Criteria(object):

    def __init__(self, section=None,pattern=None,pattern_type=None, title_regexp=None,title_exclude=None,author_regexp=None, id_regexp=None, \
                       sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=5):
        self.pattern       = pattern
        self.pattern_type  = pattern_type
        self.title_regexp  = title_regexp
        self.title_exclude = title_exclude
        self.author_regexp = author_regexp
        self.id_regexp     = id_regexp
        self.max_results   = max_results
        self.sortby        = sortby
        self.nsfw          = nsfw

        if section: # read criteria in config file
          self.pattern=config.get(section, "pattern").decode('utf8')
          if config.has_option(section, "type"):
              self.pattern_type=config.get(section, "type").decode('utf8')
          if config.has_option(section, "title_regexp"):
              self.title_regexp=config.get(section, "title_regexp").decode('utf8')
          if config.has_option(section, "title_exclude"):
              self.title_exclude=config.get(section, "title_exclude").decode('utf8')
          if config.has_option(section, "id_regexp"):
              self.id_regexp=config.get(section, "id_regexp").decode('utf8')
          if config.has_option(section, "author_regexp"):
              self.author_regexp=config.get(section, "author_regexp").decode('utf8')
          if config.has_option(section, "max_results"):
              self.max_results=config.getint(section, "max_results")

class UniqQueue(Queue):
    def __init__(self):
        self.queue=Queue() 
        self.all_items = set()

    def put(self, item):
        if item not in self.all_items:
            self.queue.put(item) 
            self.all_items.add(item)
        else:
            print("duplicate item in queue",file=stdout)


def do_search(search_queue,down_queue):
  try:
    while True:
      try:
          searchboob=search_queue.get(block=False)
      except Empty:
          if search_queue.empty():
              try:
                  downloadboob=down_queue.get(block=False)
              except Empty:
                  print("Nothing left to download",file=stdout)
              else:
                  downloadboob.download()
          if search_queue.empty():
            print("Nothing left to search",file=stdout)
            break
      else:
          videos=searchboob.search()
          if videos:
              for video in videos:
                if video:
                  down_queue.put(Downloadboob(video,searchboob.backend_name, searchboob.download_directory, searchboob.links_directory))
  except KeyboardInterrupt:
    print("Shutdown requested...exiting")
    exit(0)





#==================================================================================================
#======================================= START ====================================================
#==================================================================================================
# Initialize some variables and default values
DOWNLOAD_DIRECTORY=".files"
devnull=open('/dev/null', 'w', encoding="utf-8")
nproc=1#cpu_count()

verbosity=1

if verbosity>=1:
  stderr=sys.stderr
else:
  stderr=devnull
if verbosity>=2:
  stderr2=sys.stderr
else:
  stderr2=devnull
  sys.tracebacklimit = 0
if verbosity>=3:
  stdout=sys.stdout
else:
  stdout=devnull 

# check what is available
exec_videoob=check_exec('videoob')
exec_wget=check_exec('wget')
exec_curl=check_exec('curl')
exec_avconv=check_exec('avconv')
exec_ffmpeg=check_exec('ffmpeg')
exec_rtmpdump=check_exec('rtmpdump')
exec_mimms=check_exec('mimms')

if not exec_videoob:
    print('I need videoob !')
    exit(1)

# Start parsing the config file
config = ConfigParser.ConfigParser()
config.read(['/etc/downloadboob.conf', os.path.expanduser('~/downloadboob.conf'), 'downloadboob.conf'])

try:
    links_directory=os.path.expanduser(config.get('main','directory', '.')).decode('utf8')
except ConfigParser.NoSectionError:
    print("Please create a configuration file (see the README file and the downloadboob.conf example file)")
    exit(2)

download_directory=os.path.join(links_directory, DOWNLOAD_DIRECTORY)

print("Downloading to %s" % (links_directory))

if config.has_option("main", "live"):
    down_live=config.getboolean("main", "live")
else:
    down_live=False

if config.has_option("main", "kodi"):
    kodi=config.getboolean("main", "kodi")
else:
    kodi=False

if config.has_option("main", "backend_directory"):
    backend_directory=os.path.expanduser(config.get("main", "backend_directory").decode('utf8'))
else:
    backend_directory=os.path.expanduser("~/.local/share/weboob/modules/1.0/")

if config.has_option("main", "verbosity"):
    verbosity=config.getint("main", "verbosity")
    if verbosity>=1:
      stderr=sys.stderr
    else:
      stderr=devnull
    if verbosity>=2:
      stderr2=sys.stderr
      sys.tracebacklimit = 20
    else:
      stderr2=devnull
      sys.tracebacklimit = 0
    if verbosity>=3:
      stdout=sys.stdout
    else:
      stdout=devnull 

# Update the modules
print("Backends update",file=stdout)
Popen(["weboob-config","update"],stdout=stdout,stderr=stderr).wait()

# Start the serious thing
if __name__ == '__main__':
  search_queue=UniqQueue()
  down_queue=UniqQueue()
  for section in config.sections():
    if section != "main":
        section_backend_name=config.get(section, "backend").decode('utf8')
        section_sublinks_directory=config.get(section,"directory").decode('utf8')
        section_links_directory=os.path.join(links_directory, section_sublinks_directory)

        purge(section_links_directory)

        # read criteria in config file
        section_criteria = Criteria(section)

        searchboob = Searchboob(section_backend_name, download_directory,section_criteria,section_links_directory)

        if check_backend(searchboob.backend_name):
          search_queue.put(searchboob) 
          print("Search for %s in queue" % section,file=stdout)

          if section_criteria.pattern_type == "search": # FIXME (AT LEAST) FOR YOUTUBE
              section_criteria.sortby=CapVideo.SEARCH_RELEVANCE
              searchboob=Searchboob(section_backend_name, download_directory,section_criteria,section_links_directory)
              search_queue.put(searchboob) 
              print("Search-bis for %s in queue" % section,file=stdout)

  print("Nombre de recherches à effectuer : "+str(search_queue.queue.qsize()),file=stdout)
  processes = [Process(target=do_search,args=(search_queue.queue,down_queue.queue,)) for i in range(nproc)]
  for p in processes:
    p.start()
  for p in processes:
    p.join()


exit(0)



