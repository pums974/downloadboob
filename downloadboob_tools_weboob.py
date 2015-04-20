# !/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Tools used for downloadboob

    We will put here, functions directly relating to weboob
"""
__author__ = 'Alexandre Poux'

from datetime import datetime, timedelta

from weboob.capabilities.video import BaseVideo

from downloadboob_tools_generic import *


def backend_is_installed(backend_name):
    """
        Check is backen is installed by asking videoob
        :param backend_name:
        :return:
    """
    output, error = Popen(['videoob', "backend", "list"],
                          stdout=PIPE,
                          stderr=PIPE).communicate()
    if error:
        logging.info(error.decode('utf8'))
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
        :param backend_name:
        :return:
    """
    output, error = Popen(["videoob", "backend", "list-modules"],
                          stdout=PIPE,
                          stderr=PIPE).communicate()
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
        :param backend_name:
        :return:
    """
    print('Installing backend %s' % backend_name)
    process = Popen(["videoob", "backend", "add", backend_name],
                    stdout=PIPE,
                    stderr=PIPE)
    output, error = process.communicate()
    res = process.wait()
    logging.info(output)
    if not error:
        logging.info('Backend %s installed with no problem' % backend_name)
        return res == 0
    logging.error(error)
    logging.error('Error during installation of Backend %s' % backend_name)
    return False


def check_backend(backend_name):
    """
        Check if the backend is installed
        :rtype : logical
        :param backend_name:
        :return:
    """
    logging.debug('Checking Backend %s' % backend_name)
    if not backend_is_installed(backend_name):
        if backend_is_installable(backend_name):
            if install_backend(backend_name):
                return True
        return False
    return True


def videoob_get_info(backend, video):  # THIS IS COSTLY
    """
        Fetch info for the video
        :param video:
        :param backend:
    """
    logging.debug('Getting infos for video %s' % video.id)
    try:
        backend.fill_video(video, ('ext', 'title', 'url', 'duration',
                                   'author', 'date', 'description'))
    except Exception as test2:
        if video.title:
            logging.debug(
                "Impossible to find info about the video %s :\n%s : %s" %
                (video.id + " - " + video.title, type(test2).__name__,
                 test2))
        else:
            logging.debug(
                "Impossible to find info about the video %s :\n%s : %s" %
                (video.id, type(test2).__name__, test2))
    try:
        output, error = Popen(['videoob', "info", "--backend=" + backend.name,
                               "--", video.id],
                              stdout=PIPE,
                              stderr=PIPE).communicate()
        output = output.decode('utf8')
        if error:
            logging.error(error.decode('utf8'))
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
                    video.date = datetime.strptime(suffix[0:19],
                                                   "%Y-%m-%d %H:%M:%S")

    except CalledProcessError as test1:
        if video.title:
            logging.debug("videoob info for %s failed : \n%s : %s" %
                          (video.id + " - " + video.title,
                           type(test1).__name__, test1))
        else:
            logging.debug("videoob info for %s failed : \n%s : %s" %
                          (video.id, type(test1).__name__, test1))


def videoob_list_rep(rep, backend):
    """
        List video available for the backend asif it was a directory
        :param rep:
        :param backend:
        :return:
    """
    logging.debug("Listing videos")
    list_id = []
    list_rep = list(backend.iter_resources((BaseVideo, ), rep.split("/")))
    for fich in list_rep:
        if fich.id:
            list_id.append(fich.id)
        else:
            list_id.append(videoob_list_rep(rep + "/" + fich.title, backend))
    return sorted(set(list_id))
