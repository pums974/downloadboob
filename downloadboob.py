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

import subprocess
import os
import re

import ConfigParser

from weboob.core import Weboob
from weboob.capabilities.base import NotLoadedType
from weboob.capabilities.video import CapVideo,BaseVideo

from subprocess import Popen, check_output,call,CalledProcessError
from datetime import datetime,timedelta

from multiprocessing import Pool,Process,Queue,cpu_count
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

def write_file(f,string):
    f.write(string.encode('utf8'))

def check_backend(backend_name):
    output = check_output(['videoob', "backend","list"],stderr=devnull,shell=False, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8')
    list_backend = output.splitlines()[0].split(": ")[1].split(", ")
    if backend_name in list_backend:
        return True
    else:
        output = check_output(["videoob","backend","list-modules"],stderr=devnull,shell=False, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8')
        list_backend=[]
        for line in output.splitlines():
          if not matched(line,"Modules list:"):
            list_backend.append(line.split("] ")[1].split(" ")[0])
        if backend_name in list_backend:
            p=Popen(["videoob","backend","add",backend_name],stderr=devnull,stdout=devnull,shell=False)
            return p.wait() == 0
        else:
            return False

DOWNLOAD_DIRECTORY=".files"
devnull=open('/dev/null', 'w')

def check_exec(executable):
    if call(['which', executable],stderr=devnull,stdout=devnull,shell=False) != 0:
        return False
    return True

def matched(string, regexp):
    if regexp and string:
        return re.search(regexp, string) is not None
    return None

class Downloadboob(object):

    def __init__(self, name,backend_name, download_directory, links_directory):
        self.download_directory = download_directory
        self.links_directory = links_directory
        self.backend_name = backend_name
        self.backend = None
        self.weboob = Weboob()
        self.weboob.load_backends(modules=[self.backend_name])
        self.backend=self.weboob.get_backend(self.backend_name)
        self.name = name

    def check_link(self, link_name):
        if os.path.islink(link_name):
            file_name = os.readlink(link_name)
            absolute_file_name = os.path.join(self.links_directory, file_name)
            if os.path.isfile(absolute_file_name):
                return True
            return False
        else:
            return True

    def is_downloaded(self, video):
        if os.path.isfile(self.get_filename(video)) or os.path.isfile(self.get_filename(video,m3u=True)):
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

    def get_linkname(self, video,m3u=False):
        if not os.path.exists(self.links_directory):
            os.makedirs(self.links_directory)
        if not m3u:
          ext = video.ext
          if not ext:
              ext = 'avi'
        else:
          ext='m3u'
        if not kodi:
            misc = video.date.strftime("%y-%m-%d")
            if not misc:
                misc = video.id
            return "%s/%s (%s).%s" % (self.links_directory, removeSpecial(video.title), removeSpecial(misc), ext)
        else:
            return "%s/%s.%s" % (self.links_directory, removeSpecial(video.title), ext)

    def rewrite_title(self, video): #FOR KODI
        video.title = "S00E00 - "+video.title+" ("+str(video.id)+")"

    def videoob_list_rep(self,rep,backend):
        list_id=[]
        list_rep=list(self.backend.iter_resources((BaseVideo,), rep.split("/")))
        for fich in list_rep:
            if fich.id:
               list_id.append(fich.id)
            else:
               list_id.append(self.videoob_list_rep(rep+"/"+fich.title,backend))
        return sorted(set(list_id))

    def videoob_get_info(self,video): # THIS IS COSTLY
        try:
            output = check_output(['videoob', "info",video.id+"@"+self.backend.name],stderr=devnull,shell=False, env={"PYTHONIOENCODING": "UTF-8"}).decode('utf8')
            for line in output.splitlines():
                prefix=line.split(": ")[0]
                suffix=line[len(prefix)+2:]
                if matched(prefix,"ext"):
                    video.ext=suffix
                elif matched(prefix,"title"):
                    video.title=suffix
                elif matched(prefix,"description"):
                    video.description=suffix
                elif matched(prefix,"url"):
                    video.url=suffix
                elif matched(prefix,"author"):
                    video.author=suffix
                elif matched(prefix,"duration"):
                    t=datetime.strptime(suffix,"%H:%M:%S")
                    video.duration=timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
                elif matched(prefix,"date") and suffix:
                    video.date=datetime.strptime(suffix,"%Y-%m-%d %H:%M:%S")
        except CalledProcessError:
            self.backend.fill_video(video, ('ext','title', 'url', 'duration', 'author', 'date', 'description')) # BUGGY FOR ARTE

    def purge(self):
        #remove link if file have been removed
        if not os.path.isdir(self.links_directory):
            return
        dirList=os.listdir(self.links_directory)
        for local_link_name in dirList:
            link_name = self.links_directory + "/" + local_link_name
            if not self.check_link(link_name):
                print("Remove %s" % link_name)
                os.remove(link_name)

    def init_dir(self):
        # create directory
        if not os.path.isdir(self.links_directory):
            print("  create link directory : %s" % self.links_directory)
            os.makedirs(self.links_directory)
        if kodi:
            file_name = os.path.join(self.links_directory, 'tvshow.nfo')
            Show_name = self.links_directory.split("/")[-1]
            if not os.path.isfile(file_name):
                print("  create %s" % file_name)
                f=open(file_name,'w')
                write_file(f,"<tvshow>\n")
                write_file(f,"  <title>"+Show_name+"</title>\n")
                write_file(f,"</tvshow>\n")
                f.close()

    def do_search(self, pattern=None,pattern_type="search", sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False):
        list_videos=[]
        if matched(pattern_type,"search"):
            list_videos=self.backend.search_videos(pattern, sortby, nsfw)
        elif matched(pattern_type,"ls"):
            for id in self.videoob_list_rep(pattern,self.backend.name):
                sys.path.insert(0,backend_directory+"/"+self.backend.name+"/" ) # HACK
                if 'video' in sys.modules:
                   del sys.modules['video']
                if matched(self.backend.name,"arte"):
                   from video import ArteVideo as video_init
                elif matched(self.backend.name,"canalplus"):
                   from video import CanalplusVideo as video_init
                elif matched(self.backend.name,"arretsurimages"):
                   from video import ArretSurImagesVideo as video_init
                elif matched(self.backend.name,"dailymotion"):
                   from video import DailymotionVideo as video_init
                elif matched(self.backend.name,"nolifetv"):
                   from video import NolifeTVVideo as video_init
                elif matched(self.backend.name,"youtube"):
                   from video import YoutubeVideo as video_init
                list_videos.append(video_init(id))
        return list_videos

    def filter_list(self,list_videos,title_regexp,id_regexp,author_regexp,title_exclude,max_results):
        videos = []
        i=0
        for video in list_videos:
            if self.is_ok(video,title_regexp,id_regexp,author_regexp,title_exclude):
                self.videoob_get_info(video)
                if video and video.url:
                    if self.is_ok(video,title_regexp,id_regexp,author_regexp,title_exclude):
                        i+=1
                        if not self.is_downloaded(video):
                            videos.append(video)
#                            print("  %s\n    Description:%s\n    Author:%s\n    Id:%s\n    Duration:%s\n    Date:%s" % (video.title,video.description,video.author, video.id, video.duration, video.date))
#                        else:
#                            print("Already downloaded, check %s" % video.id)
                        if i == max_results:
                            break
#                elif not video:
#                    print('Video not found: %s' %  video, file=sys.stderr)
#                elif not video.url:
#                    print('Error: the URL is not available : '+str(video.url), file=sys.stderr)
        return videos

    def write_m3u(self, video):
        if matched(video.ext,"m3u"):
            return self.do_download(video,conv=False)
        else:
            if matched(video.url,"\.m3u"):
                return self.do_download(video,conv=False)
            else:
                dest = self.get_filename(video,m3u=True)
                Show_name = self.links_directory.split("/")[-1]
                print("  create %s" % dest)
                f=open(dest, 'w')
                write_file(f,"#EXTINF: ")
                if video.duration:
                   write_file(f,str(video.duration))
                else:
                   write_file(f,str(-1))
                write_file(f,", "+Show_name+" - "+video.title+"\n")
                write_file(f,video.url) 
                f.close()
                return 0

    def do_download(self, video):
        dest = self.get_filename(video)
        if video.url.startswith('rtmp'):
            if not check_exec('rtmpdump'):
                print('I Need rtmpdump')
                return 1
            args = ['rtmpdump', '-e', '-r', video.url, '-o', dest]
        elif video.url.startswith('mms'):
            if not check_exec('mimms'):
                print('I Need mimms')
                return 1
            args = ['mimms', video.url, dest]
        else:
            if not check_exec('wget'):
                if not check_exec('curl'):
                    print('I Need curl or wget')
                    return 1
                else:
                    args = ['curl','-s', video.url, '-o', dest]
            else:
                args = ['wget','-q', video.url, '-O', dest]
        return call(args,stderr=devnull,stdout=devnull,shell=False)

    def do_conv(self, video):
        dest = self.get_filename(video)
        if matched(str(video.ext),"m3u"):
           video.ext='avi'
           dest = self.get_filename(video)
           if not check_exec('avconv'):
              if not check_exec('ffmpeg'):
                 print('I Need avconv or ffmpeg')
                 return 1
              else:
                 args = ['ffmpeg','-i', video.url, '-vcodec','copy','-acodec','copy','-loglevel','error', dest] #"-stat" ,'-threads', '8'
           else:
              args = ['avconv','-i', video.url, '-c','copy', dest]
           return call(args,stderr=devnull,stdout=devnull,shell=False)
        else:
           return 0

    def set_link(self, video,m3u=False):
        linkname = self.get_linkname(video,m3u=m3u)
        idname = self.get_filename(video, relative=True,m3u=m3u)
        absolute_idname = self.get_filename(video, relative=False,m3u=m3u)
        if not os.path.islink(linkname) and os.path.isfile(absolute_idname):
#            print("%s -> %s" % (linkname, idname))
            os.symlink(idname, linkname)

    def do_mv(self, video,m3u=False):
        linkname = self.get_linkname(video,m3u=m3u)
        idname = self.get_filename(video, relative=True,m3u=m3u)
        absolute_idname = self.get_filename(video, relative=False,m3u=m3u)
        if not os.path.isfile(linkname) and os.path.isfile(absolute_idname):
#            print("%s -> %s" % (absolute_idname,linkname))
            os.rename(absolute_idname, linkname)
            open(absolute_idname, 'w').close() 

    def write_nfo(self, video):
        nfoname, _ = os.path.splitext(self.get_linkname(video))
        nfoname = nfoname+".nfo"
        if not os.path.isfile(nfoname):
            Show_name = self.links_directory.split("/")[-1]
#            print("  create %s" % nfoname)
            f=open(nfoname,'w')
            write_file(f,"<episodedetails>\n")
            write_file(f,"  <title>"+video.title+"</title>\n")
            write_file(f,"  <showtitle>"+Show_name+"</showtitle>\n")
            write_file(f,"  <season>0</season>\n")
            write_file(f,"  <episode>0</episode>\n")
            if video.date:
                  write_file(f,"  <aired>"+video.date.strftime("%y/%m/%d")+"</aired>\n")
            if video.duration:
                  write_file(f,"  <runtime>"+str(int(video.duration.total_seconds()/60))+"</runtime>\n")
            if video.author:
                  write_file(f,"  <studio>"+video.author+"</studio>\n")
            else:
                  write_file(f,"  <studio>"+self.backend_name+"</studio>\n")
            if video.description:
                  write_file(f,"  <plot>"+video.description+"</plot>\n")
            write_file(f,"  <displayseason />\n")
            write_file(f,"  <displayepisode />\n")
            write_file(f,"</episodedetails>\n")
            f.close()

    def download(self, pattern=None, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=False, max_results=50, title_regexp=None, id_regexp=None, \
                 pattern_type="search",author_regexp=None,title_exclude=None):

        # create directory for links
        self.init_dir()

        # search for videos
        list_videos=self.do_search(pattern,pattern_type, sortby, nsfw)

        # Filter the list of videos
        videos = self.filter_list(list_videos,title_regexp,id_regexp,author_regexp,title_exclude,max_results)

        # download videos
        if videos:
            for video in videos:
                print("Downloading... "+video.title)
                if kodi:                            # THE "TITLE" BECOME "S00E00 - TITLE (ID)"
                    self.rewrite_title(video)
                if down_live:                       # CREATE LIVE STREAM
                    ret=self.write_m3u(video)
                else:                               # DOWNLOAD VIDEO
                    ret=self.do_download(video)         # FOR DIRECT LINKS
                    if not ret: ret=self.do_conv(video) # FOR INDIRECT LINKS
                if not ret:
                    if not kodi:
                        self.set_link(video)        # CREATE LINKS FOR A BEAUTIFULL LIBRARY
                    else:
                        self.do_mv(video)           # MOVE FILES FOR A BEAUTIFULL LIBRARY
                        self.write_nfo(video)       # CREATE NFO FILES FOR KODI
                    print("Downloaded :"+video.title)
                else:
                    print("Failed download :"+video.title)




nproc=cpu_count()
def do_work(q,r):
  while True:
    try:
        section=q.get(block=False)
        backend_name=config.get(section, "backend").decode('utf8')
        if check_backend(backend_name):
          pattern=config.get(section, "pattern").decode('utf8')
          section_sublinks_directory=config.get(section,"directory").decode('utf8')
          if config.has_option(section, "type"):
              pattern_type=config.get(section, "type").decode('utf8')
          else:
              pattern_type="search"
          if config.has_option(section, "title_regexp"):
              title_regexp=config.get(section, "title_regexp").decode('utf8')
          else:
              title_regexp=None
          if config.has_option(section, "title_exclude"):
              title_exclude=config.get(section, "title_exclude").decode('utf8')
          else:
              title_exclude=None
          if config.has_option(section, "id_regexp"):
              id_regexp=config.get(section, "id_regexp").decode('utf8')
          else:
              id_regexp=None
          if config.has_option(section, "author_regexp"):
              author_regexp=config.get(section, "author_regexp").decode('utf8')
          else:
              author_regexp=None
          if config.has_option(section, "max_results"):
              max_result=config.getint(section, "max_results")
          else:
              max_result=50
          section_links_directory=os.path.join(links_directory, section_sublinks_directory)

          downloadboob = Downloadboob(section,backend_name, download_directory, section_links_directory)
          downloadboob.purge()

          print("For backend %s, start search for '%s'" % (backend_name,section))
          downloadboob.download(pattern, CapVideo.SEARCH_DATE, False, max_result, title_regexp, id_regexp,pattern_type,author_regexp,title_exclude)
          if matched(pattern_type,"search"):
              # FIXME (AT LEAST) FOR YOUTUBE
              downloadboob.download(pattern, CapVideo.SEARCH_RELEVANCE, False, max_result, title_regexp, id_regexp,pattern_type,author_regexp,title_exclude)
          print("For backend %s, end search for '%s'" % (backend_name,section))
        else:
          print(backend_name+" unknown")
    except Empty:
      if q.empty():
        break

if not check_exec('videoob'):
    exit(1)

config = ConfigParser.ConfigParser()
config.read(['/etc/downloadboob.conf', os.path.expanduser('~/downloadboob.conf'), 'downloadboob.conf'])

try:
    links_directory=os.path.expanduser(config.get('main','directory', '.')).decode('utf8')
except ConfigParser.NoSectionError:
    print("Please create a configuration file (see the README file and the downloadboob.conf example file)")
    sys.exit(2)

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

print("Backends update")
Popen(["weboob-config","update"]).wait()


if __name__ == '__main__':
  work_queue=Queue()
  res_queue=Queue()
  for section in config.sections():
    if section != "main":
      work_queue.put(section)
  processes = [Process(target=do_work,args=(work_queue,res_queue,)) for i in range(nproc)]
  for p in processes:
    p.start()
  for p in processes:
    p.join()


exit(0)



