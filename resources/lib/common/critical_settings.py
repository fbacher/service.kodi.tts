# -*- coding: utf-8 -*-
"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""
from .imports import *

from functools import wraps
from logging import Logger as Python_Logger
from logging import (Handler, LogRecord, NOTSET)
import os
import re
import sys
import threading
import traceback

import xbmc
import six
from kutils.kodiaddon import Addon


class CriticalSettings(object):
    """
        A subset of settings that are used by modules which can not have a
        dependency on Settings.

    """
    ADDON_ID = 'service.kodi.tts'

    addon = None
    try:
        addon = Addon(ADDON_ID)
    except (Exception):
        xbmc.log('addon {} was not found.'.format(ADDON_ID),
                 level=xbmc.LOGERROR)

    @staticmethod
    def is_debug_enabled():
        # type: () -> bool
        """

        :return:
        """
        if CriticalSettings.addon is None:
            return False

        is_debug_enabled = CriticalSettings.addon.setting('debug')
        return bool(is_debug_enabled)

    @staticmethod
    def get_logging_level():
        # type: () -> int
        """

        :return:
        """
        log_level = 30
        xbmc.log('get_logging_level', level=xbmc.LOGDEBUG)

        try:

            # log_level is a 0-based enumeration in increasing verbosity
            # Convert to values utilized by our Python logging library
            # based config_logger:
            #  FATAL = logging.CRITICAL # 50
            #  SEVERE = 45
            #  ERROR = logging.ERROR       # 40
            #  WARNING = logging.WARNING   # 30
            #  NOTICE = 25
            #  INFO = logging.INFO         # 20
            #  DEBUG_EXTRA_VERBOSE = 15
            #  DEBUG_VERBOSE = 12
            #  DEBUG = logging.DEBUG       # 10
            #  NOTSET = logging.NOTSET     # 0

            # WARNING|NOTICE|INFO|DEBUG|VERBOSE DEBUG|EXTRA VERBOSE DEBUG"

            translated_value = 3
            try:
                CriticalSettings.addon
            except (NameError):
                CriticalSettings.addon = None
                xbmc.log('addon was not defined.', level=xbmc.LOGDEBUG)

            if CriticalSettings.addon is None:
                xbmc.log('Can not access script.video.randomtrailers',
                         level=xbmc.LOGERROR)
                translated_value = 3
            else:
                log_level = CriticalSettings.addon.setting('log_level')
                msg = 'got log_level from settings: {!s}'.format(log_level)
                xbmc.log(msg, level=xbmc.LOGDEBUG)
                translated_value = 0
                if log_level == '0':  # Warning
                    translated_value = 30
                elif log_level == '1':  # Notice
                    translated_value = 25
                elif log_level == '2':  # Info
                    translated_value = 20
                elif log_level == '3':  # Debug
                    translated_value = 10
                elif log_level == '4':  # Verbose Debug
                    translated_value = 8
                elif log_level == '5':  # Extra Verbose Debug
                    translated_value = 6

                # prefix = '[Thread {!s} {!s}.{!s}:{!s}]'.format(
                # record.threadName, record.name, record.funcName,
                # record.lineno)
                msg = 'get_logging_level got log_level: {!s}'.format(
                    translated_value)
                xbmc.log(msg, level=xbmc.LOGDEBUG)
        except (Exception):
            xbmc.log('Exception occurred in get_logging_level',
                     level=xbmc.LOGERROR)

        return translated_value
