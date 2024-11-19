# -*- coding: utf-8 -*-

"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""

import locale
import os
from enum import IntEnum
from pathlib import Path

import xbmc
import xbmcvfs

from common import *
from common.kodiaddon import Addon

addonName = 'service.kodi.tts'
addon = Addon(addonName)


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

    CACHE_SUFFIX: Final[str] = 'cache_suffix'
    LOCALE = ''
    MAX_PHRASE_LENGTH: Final[str] = 'max_phrase_length'

    MPV_PATH_LINUX: Final[str] = '/usr/bin/mpv'
    MPLAYER_PATH_LINUX: Final[str] = '/usr/bin/mplayer'
    MPV_PATH_WINDOWS: Final[str] = 'mpv.exe'
    MPLAYER_PATH_WINDOWS: Final[str] = 'mplayer.exe'
    MPLAYER_PATH: str = None
    MPV_PATH: str = None

    NAME: Final[str] = 'name'
    PAUSE_INSERT = '...'
    PLATFORM_WINDOWS: bool = False

    @staticmethod
    def static_init() -> None:
        """
            Assign calculated values

        :return:
        """
        Constants.KODI_ADDON = addon  # From kutils import addon, same as
        # kodiaddon.Addon()
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

        Constants.ADDON_DIRECTORY = xbmcvfs.translatePath(str(addon.PATH))
        Constants.BACKENDS_DIRECTORY = os.path.join(
                Constants.PYTHON_ROOT_PATH, 'backends')
        Constants.DISABLE_PATH = os.path.join(addon.DATA_PATH, 'DISABLED')
        Constants.ENABLE_PATH = os.path.join(addon.DATA_PATH, 'ENABLED')
        Constants.DEFAULT_CACHE_DIRECTORY = os.path.join(Constants.USER_DATA_PATH,
                                                         'cache')
        Constants.LOCALE, encoding = locale.getdefaultlocale()

        Constants.PLATFORM_WINDOWS = xbmc.getCondVisibility('System.Platform.Windows')
        if xbmc.getCondVisibility('System.Platform.Windows'):
            mpv_dir = os.environ.get('MPV_PATH', '')
            if mpv_dir:
                Constants.MPV_PATH = str(Path(mpv_dir) / Constants.MPV_PATH_WINDOWS)
            else:
                Constants.MPV_PATH = Constants.MPV_PATH_WINDOWS
            xbmc.log(f'mpv_dir: {mpv_dir} MPV_PATH: {Constants.MPV_PATH}', xbmc.LOGDEBUG)

            mplayer_dir: str = os.environ.get('MPLAYER_PATH', None)
            xbmc.log(f'mplayer_path1: {mplayer_dir} '
                     f'PROGRAMFILES: {os.environ.get("PROGRAMFILES", None)}',
                     xbmc.LOGDEBUG)
            if not mplayer_dir:
                mplayer_dir = os.environ.get('PROGRAMFILES', None)
                if mplayer_dir:
                    mplayer_dir = str(Path(mplayer_dir) / 'Mplayer')
            if mplayer_dir:
                Constants.MPLAYER_PATH = str(Path(mplayer_dir) /
                                             Constants.MPLAYER_PATH_WINDOWS)
            xbmc.log(f'mplayer_dir: {mplayer_dir} MPLAYER_PATH: '
                     f'{Constants.MPLAYER_PATH}', xbmc.LOGDEBUG)
        else:
            Constants.MPV_PATH = Constants.MPV_PATH_LINUX
            Constants.MPLAYER_PATH = Constants.MPLAYER_PATH_LINUX


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
    NO_PHRASES = 12
    NOT_SET = 99
