# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Tools used for downloadboob

    We put here functions directly relating to weboob

    .. seealso:: weboob
    .. note:: videoob_get_info is very costly
    .. todo:: optimize videoob_get_info
"""
__author__ = 'Alexandre Poux'

from datetime import datetime, timedelta
from weboob.capabilities.video import BaseVideo
from downloadboob_tools_generic import *

def check_backend(backend_name):
    """
        Check if the backend is installed, if not try to install it
        :param backend_name: Name of the backend we want
        :type backend_name: string
        :return: True if backend available and installed, False otherwise
        :rtype : logical
    """
    logging.debug('Checking Backend %s' % backend_name)
    if not backend_is_installed(backend_name):
        if backend_is_installable(backend_name):
            if install_backend(backend_name):
                return True
        return False
    return True


def backend_is_installed(backend_name):
    """
        Check is backen is installed by asking videoob
        :param backend_name: Name of the backend we want
        :type backend_name: string
        :return: True if backend installed, False otherwise
        :rtype : logical
        .. todo:: Get rit of Popen and check with python directly
    """
    output, error = Popen(['videoob', "backend", "list"],
                          stdout=PIPE, stderr=PIPE, env=env_utf8).communicate()
    error = error.decode('utf8')
    output = output.decode('utf8')
    if error:
        logging.info(error)
    list_backend = output.splitlines()[0].split(": ")[1].split(", ")
    if backend_name in list_backend:
        logging.debug('Backend %s already installed' % backend_name)
        return True
    else:
        logging.info('Backend %s not already installed' % backend_name)
        return False


def backend_is_installable(backend_name):
    """
        Check is backen is installable by asking videoob
        :param backend_name: Name of the backend we want
        :type backend_name: string
        :return: True if backend installable, False otherwise
        :rtype : logical
        .. todo:: Get rit of Popen and check with python directly
    """
    output, error = Popen(["videoob", "backend", "list-modules"],
                          stdout=PIPE, stderr=PIPE, env=env_utf8).communicate()
    error = error.decode('utf8')
    output = output.decode('utf8')
    if error:
        logging.error(error)
    list_backend = []
    for line in output.splitlines():
        if not matched(line, "^Modules list:"):
            list_backend.append(line.split("] ")[1].split(" ")[0])
    if backend_name in list_backend:
        logging.debug('Backend %s installable' % backend_name)
        return True
    else:
        logging.info('Backend %s not installable' % backend_name)
        return False


def install_backend(backend_name):
    """
        Install backend
        :param backend_name: Name of the backend we want
        :type backend_name: string
        :return: True if backend installed, False otherwise
        :rtype : logical
        .. todo:: Get rit of Popen and install with python directly
    """
    print('Installing backend %s' % backend_name)
    process = Popen(["videoob", "backend", "add", backend_name],
                    stdout=PIPE, stderr=PIPE, env=env_utf8)
    output, error = process.communicate()
    res = process.wait()
    error = error.decode('utf8')
    output = output.decode('utf8')
    logging.info(output)
    if not error:
        logging.info('Backend %s installed with no problem' % backend_name)
        return res == 0
    logging.error(error)
    logging.error('Error during installation of Backend %s' % backend_name)
    return False


def videoob_get_info(backend, video):  # THIS IS COSTLY
    """
        Fetch info for the video
        :param video: The video we want to know more about
        :param backend: The backend to ask for info
        :type video: video
        :type backend: backend
        :return: video filled with infos
        :rtype : None
        .. warnings:: THIS IS VERY COSTLY
        .. todo:: optimize
    """
    logging.debug('Getting infos for video %s' % video.id)
    videoob_get_info_with_python(backend, video)
    videoob_get_info_with_subprocess(backend, video)


def videoob_get_info_with_python(backend, video):
    """
        Fetch info for the video via python
        :param video: The video we want to know more about
        :param backend: The backend to ask for info
        :type video: video
        :type backend: backend
        :return: video filled with infos
        :rtype : None
        .. warnings:: THIS IS VERY COSTLY
        .. todo:: optimize
    """
    try:
        if backend.name == "arte":
            backend.fill_arte_video(video, ('ext', 'title', 'url', 'duration',
                                       'author', 'date', 'description'))
        else:
            backend.fill_video(video, ('ext', 'title', 'url', 'duration',
                                       'author', 'date', 'description'))
    except Exception as e:
        if video.title:
            logging.debug(
                "Impossible to use python to find info about the video %s :\n%s : %s" %
                (video.id + " - " + video.title, type(e).__name__, e))
        else:
            logging.debug(
                "Impossible to use python to find info about the video %s :\n%s : %s" %
                (video.id, type(e).__name__, e))


def videoob_get_info_with_subprocess(backend, video):
    """
        Fetch info for the video via subprocess
        :param video: The video we want to know more about
        :param backend: The backend to ask for info
        :type video: video
        :type backend: backend
        :return: video filled with infos
        :rtype : None
        .. warnings:: THIS IS VERY COSTLY
        .. todo:: optimize
    """
    output, error = Popen(['videoob', "info", "--backend=" + backend.name,
                           "--", video.id], stdout=PIPE, stderr=PIPE, env=env_utf8).communicate()
    error = error.decode('utf8')
    output = output.decode('utf8')
    if error:
        logging.error(error)
    for line in output.splitlines():
        prefix = line.split(": ")[0]
        suffix = line[len(prefix) + 2:]
        if suffix:
            if prefix == "ext":
                video.ext = suffix
            elif prefix == "title":
                video.title = suffix
            elif prefix == "description":
                video.description = suffix
            elif prefix == "url":
                video.url = suffix
            elif prefix == "author":
                video.author = suffix
            elif prefix == "duration":
                t = datetime.strptime(suffix, "%H:%M:%S")
                video.duration = timedelta(hours=t.hour,
                                           minutes=t.minute,
                                           seconds=t.second)
            elif prefix == "date":
                try:
                    video.date = datetime.strptime(suffix[0:19],
                                                   "%Y-%m-%d %H:%M:%S")
                except:
                    video.date = datetime.strptime(suffix[0:19],
                                                   "%Y-%m-%d")


def videoob_list_rep(rep, backend):
    """
        List video available in a directory for a backend
        :param rep: fictive path we want to list
        :param backend: backend to ask
        :type rep: string
        :type backend: backend
        :return: List of video in the directory rep
        :rtype : [string,]
    """
    logging.debug("Listing videos")
    list_id = []
    if not type(rep) is list:
        rep = rep.split("/")
    try:
        list_dir = list(backend.iter_resources((BaseVideo, ), rep))
    except:
        logging.info('Path not found : %s' % '/'.join(rep))
        return([])
    for elem in list_dir:
        if elem.id:  # It's a video
            list_id.append(elem.id)
        else:        # It's like a directory
            list_id.append(videoob_list_rep(elem.split_path, backend))
    return sorted(set(list_id))
