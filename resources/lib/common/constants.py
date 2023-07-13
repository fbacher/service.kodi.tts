# -*- coding: utf-8 -*-

"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""

import locale
import os
from enum import IntEnum

import xbmcvfs

from common.typing import *
from kutils.kodiaddon import Addon

addonName = 'service.kodi.tts'
addon = Addon(addonName)
from kutils import addon


class Constants:
    """
        Constants common to all plugins
    """
    INCLUDE_MODULE_PATH_IN_LOGGER = True

    ADDON_DATA = None
    ADDON_NAME = None
    ADDON_SHORT_NAME = 'service.kodi.tts'
    ADDON_UTIL = None
    ADDON = None
    ADDON_PATH = None
    PYTHON_ROOT_PATH = None
    ADDON_DIRECTORY = None
    AUTO: Final[str] = 'auto'  # Not used here
    BACKENDS_DIRECTORY = None
    MEDIA_PATH = None
    PROFILE = None
    PROFILE_PATH = None
    SCRIPT_PATH = None
    ADDON_ID = 'service.kodi.tts'
    TRACEBACK = 'LEAK Traceback StackTrace StackDump'
    LOG_PATH = None
    USER_DATA_PATH = None
    VERSION = None

    DISABLE_PATH = None
    ENABLE_PATH = None
    DEFAULT_CACHE_DIRECTORY = None
    IGNORE_CACHE_EXPIRATION_DATE: bool = True

    LOCALE = ''
    PAUSE_INSERT = '...'

    @staticmethod
    def static_init() -> None:
        """
            Assign calculated values

        :return:
        """
        Constants.KODI_ADDON = addon  # From kutils import addon, same as kodiaddon.Addon()
        Constants.ADDON = addon.addon

        Constants.ADDON_PATH = addon.PATH
        Constants.PYTHON_ROOT_PATH = os.path.join(Constants.ADDON_PATH,
                                                  'resources',
                                                  'lib')
        Constants.VERSION = addon.VERSION
        Constants.USER_DATA_PATH = xbmcvfs.translatePath("special://userdata")
        Constants.ADDON_DATA = addon.DATA_PATH
        Constants.MEDIA_PATH = addon.MEDIA_PATH
        Constants.PROFILE = addon.PROFILE
        Constants.PROFILE_PATH = xbmcvfs.translatePath(addon.PROFILE)
        Constants.SCRIPT_PATH = os.path.join(
            addon.PATH, 'resources', 'skins', 'Default', '720p')
        Constants.LOG_PATH = os.path.join(
            xbmcvfs.translatePath('special://logpath'), 'kodi.log')

        Constants.ADDON_DIRECTORY = xbmcvfs.translatePath(addon.PATH)
        Constants.BACKENDS_DIRECTORY = os.path.join(
            Constants.PYTHON_ROOT_PATH, 'backends')
        Constants.DISABLE_PATH = os.path.join(addon.DATA_PATH, 'DISABLED')
        Constants.ENABLE_PATH = os.path.join(addon.DATA_PATH, 'ENABLED')
        Constants.DEFAULT_CACHE_DIRECTORY = os.path.join(Constants.USER_DATA_PATH,
                                                         'cache')
        Constants.LOCALE, encoding = locale.getdefaultlocale()

# def info(key): Use Constants.ADDON.info()

# def configDirectory(): # Use Constants.PROFILE_PATH
# def profileDirectory(): # Use Constants.PROFILE_PATH

# def addonPath(): Use Constants.ADDON_PATH
# def backendsDirectory(): Use Constants.BACKENDS_DIRECTORY


Constants.static_init()


class DebugLevel(object):
    """

    """
    FATAL = '00_Fatal'
    SEVERE = '01_Severe'
    ERROR = '02_Error'
    WARNING = '03_Warning'
    NOTICE = '04_Notice'
    INFO = '05_Info'
    DEBUG_EXTRA_VERBOSE = '06_Debug_Extra_Verbose'
    DEBUG_VERBOSE = '07_Debug_Verbose'
    DEBUG = '08_Debug'


class Notify:
    STOP: str = 'stop'


class ReturnCode(IntEnum):
    OK = 0
    MINOR = 2
    MINOR_SAVE_FAIL = 3
    STOP = 4
    CALL_FAILED = 5
    FILE = 6
    DOWNLOAD = 7
    EXPIRED = 10
    ABORT = 11
    NOT_SET = 99
