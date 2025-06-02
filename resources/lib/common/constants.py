# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

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
    SHELL_SCRIPTS_PATH = None
    ESPEAK_PATH: Path = None
    ESPEAK_PATH_WINDOWS: Path = None
    ESPEAK_DATA_PATH: Path = None
    ESPEAK_DATA_PATH_WINDOWS: Path = None
    ADDON_DIRECTORY = None
    #  AUTO: Final[str] = 'auto'  # Not used here
    BACKENDS_DIRECTORY = None
    MEDIA_PATH = None
    KEYMAPS_PROTO_PATH: Path = None
    KEYMAPS_PATH: Path = None
    PROFILE = None
    PROFILE_PATH = None
    SCRIPT_PATH = None
    ADDON_ID = 'service.kodi.tts'
    TRACEBACK = 'LEAK Traceback StackTrace StackDump'
    LOG_PATH: Path = None
    RESOURCES_PATH: Path = None
    USER_DATA_PATH: Path = None
    VERSION = None

    DISABLE_PATH = None
    ENABLE_PATH = None
    DEFAULT_CACHE_DIRECTORY = None
    PREDEFINED_CACHE: Path | None = None
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
    # TODO: can't distinguish between constants and calculated values (was None)
    CACHE_TOP: Final[str] = 'cache_top'

    NAME: Final[str] = 'name'
    PAUSE_INSERT = '...'
    # When generating audio, first save to a temp file, then, rename to correct
    # name when successful. TEMP_AUDIO_SUFFIX is appended to the file name, not
    # the type: ex sample.mp3 becomes sample.tmp.mp3
    TEMP_AUDIO_NAME_SUFFIX = '.tmp'
    PLATFORM_WINDOWS: bool = xbmc.getCondVisibility('System.Platform.Windows')
    USE_LANGCODES_DATA: bool = not PLATFORM_WINDOWS
    # Don't voice while video is playing
    STOP_ON_PLAY: bool = True


    @staticmethod
    def static_init() -> None:
        """
            Assign calculated values

        :return:
        """
        xbmc.log(f'In constants.static_init')
        Constants.ADDON = addon.addon
        Constants.ADDON_DATA = addon.DATA_PATH
        Constants.USER_DATA_PATH = Path(xbmcvfs.translatePath("special://userdata"))
        Constants.RESOURCES_PATH = addon.PATH / 'resources'
        Constants.PYTHON_ROOT_PATH = Constants.RESOURCES_PATH / 'lib'

        Constants.ADDON_DIRECTORY = Path(xbmcvfs.translatePath(str(addon.PATH)))
        Constants.ADDON_PATH = addon.PATH
        Constants.BACKENDS_DIRECTORY = Constants.PYTHON_ROOT_PATH / 'backends'
        Constants.DISABLE_PATH = addon.DATA_PATH / 'DISABLED'
        Constants.DEFAULT_CACHE_DIRECTORY = Constants.USER_DATA_PATH / 'cache'
        Constants.ESPEAK_DATA_PATH = Path('/usr/lib/x86_64-linux-gnu/espeak-ng-data')
        Constants.ESPEAK_DATA_PATH_WINDOWS = \
            Path(r'C:\Program Files\eSpeak NG/espeak-ng-data')
        Constants.ESPEAK_PATH = Path('/usr/bin/espeak-ng')
        Constants.ESPEAK_PATH_WINDOWS = Path(r'C:\Program Files\eSpeak NG')

        Constants.KEYMAPS_PROTO_PATH = Constants.RESOURCES_PATH / 'keymaps'
        Constants.KEYMAPS_PATH = Constants.USER_DATA_PATH / 'keymaps'
        Constants.KODI_ADDON = addon
        Constants.LOG_PATH = Path(xbmcvfs.translatePath('special://logpath')) / 'kodi.log'
        Constants.MEDIA_PATH = addon.MEDIA_PATH
        Constants.PROFILE = addon.PROFILE
        Constants.PROFILE_PATH = xbmcvfs.translatePath(addon.PROFILE)
        Constants.SHELL_SCRIPTS_PATH = Constants.RESOURCES_PATH / 'scripts'
        Constants.SCRIPT_PATH = os.path.join(
                addon.PATH, 'resources', 'skins', 'Default', '720p')
        Constants.VERSION = addon.VERSION

        # NO_ENGINE_CACHE_DIRECTORY contains a limited set of .wav files to help
        # user get started with configuration. It is used when no recognized engine or
        # player_key is found. See PlaySFXAudioPlayer, NoEngine and Google engine for
        # more information
        Constants.PREDEFINED_CACHE = (Constants.RESOURCES_PATH / 'predefined'
                                      / 'cache')
        Constants.LOCALE, encoding = locale.getdefaultlocale()

        if Constants.PLATFORM_WINDOWS:
            espeak_dir: str = os.environ.get('ESPEAK_PATH', '')
            if espeak_dir:
                Constants.ESPEAK_PATH = Path(espeak_dir)
            else:
                xbmc.log(f'No Path found for espeak-ng {espeak_dir}', xbmc.LOGINFO)
            espeak_data_dir: str = os.environ.get('ESPEAK_DATA_PATH', '')
            if espeak_data_dir:
                Constants.ESPEAK_DATA_PATH = Path(espeak_data_dir)
            else:
                xbmc.log(f'No Path found for espeak-ng data_dir {espeak_data_dir}',
                         xbmc.LOGINFO)

            mpv_dir = os.environ.get('MPV_PATH', '')
            xbmc.log(f'mpv_dir: {mpv_dir}')
            if mpv_dir:
                Constants.MPV_PATH = str(Path(mpv_dir) / Constants.MPV_PATH_WINDOWS)
                xbmc.log(f'mpv_dir now: {mpv_dir} mpv_path_windows: '
                         f'{Constants.MPV_PATH_WINDOWS}')
            else:
                Constants.MPV_PATH = Constants.MPV_PATH_WINDOWS
                xbmc.log(f'Not so good mpv_dir: {mpv_dir}')
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
