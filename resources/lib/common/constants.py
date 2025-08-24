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

DEBUG_LOGGING: bool = True


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

    # The following external commands Paths are defined here.
    # There is a default location and then there is an environment
    # variable to fall back on. Should probably use 'where' command on
    # windows (command.com) or 'whereis' on Linux

    ESPEAK_PATH: Path = None
    ESPEAK_PATH_WINDOWS: Path = None
    ESPEAK_PATH_LINUX: Path = '/usr/bin/espeak-ng'
    ESPEAK_COMMAND_WINDOWS: str = 'C:/Program Files/espeak NG/espeak-ng.exe'
    ESPEAK_COMMAND_LINUX: str = 'espeak-ng'
    ESPEAK_COMMAND: str = None
    ESPEAK_DATA_PATH: Path = None
    ESPEAK_DATA_PATH_WINDOWS: Path = Path('C:/Program Files/espeak NG/espeak-ng-data')
    ESPEAK_DATA_PATH_LINUX: Path = None
    # Define environment variables to use if not found in default location (ESPEAK_PATH,
    # above.
    ESPEAK_ENV_VAR: str = 'ESPEAK_PATH'
    ESPEAK_DATA_ENV_VAR: str = 'ESPEAK_DATA'

    MPV_PATH_LINUX: Final[str] = '/usr/bin/mpv'
    MPLAYER_PATH_LINUX: Final[str] = '/usr/bin/mplayer'
    MPV_PATH_WINDOWS: Final[str] = 'C:/Program Files/mpv/mpv.exe'
    MPLAYER_PATH_WINDOWS: Final[str] = 'C:/Program Files/mplayer/mplayer.exe'
    MPLAYER_PATH: str = None
    MPV_PATH: str = None
    MPV_PATH_ENV_VAR: Final[str] = 'MPV_PATH'
    MPLAYER_PATH_ENV_VAR: Final[str] = MPLAYER_PATH

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
    DEFAULT_CACHE_DIRECTORY: Path | None = None
    PREDEFINED_CACHE: Path | None = None
    IGNORE_CACHE_EXPIRATION_DATE: bool = True

    CACHE_SUFFIX: Final[str] = 'cache_suffix'
    LOCALE = ''
    CONFIG_SCRIPTS_DIR_WINDOWS: Path | None = None
    CONFIG_SCRIPT_PATH_WINDOWS: Path | None = None
    MAX_PHRASE_LENGTH: Final[str] = 'max_phrase_length'

    # TODO: can't distinguish between constants and calculated values (was None)
    CACHE_TOP: Final[str] = 'cache_top'

    NAME: Final[str] = 'name'
    PAUSE_INSERT = '...'
    ROTATE_TEMP_VOICE_DIR_SECONDS: float = 2 * 60.0
    # When generating audio, first save to a temp file, then, rename to correct
    # name when successful. TEMP_AUDIO_SUFFIX is appended to the file name, not
    # the type: ex sample.mp3 becomes sample.tmp.mp3
    TEMP_AUDIO_NAME_SUFFIX = '.tmp'
    PLATFORM_WINDOWS: bool = xbmc.getCondVisibility('System.Platform.Windows')
    USE_LANGCODES_DATA: bool = not PLATFORM_WINDOWS
    # Don't voice while video is playing
    STOP_ON_PLAY: bool = True

    NOTICE_QUEUE_LIMIT: int = 40
    # Write phrase text to cache
    SAVE_TEXT_FILES: Final[bool] = True
    SEED_CACHE_WITH_EXPIRED_PHRASES: bool = False
    # Maximum number of directories to search for un-voiced text files
    SEED_CACHE_DIR_LIMIT: int = 10
    SEED_CACHE_DELAY_START_SECONDS: float = 6 * 60.0
    SEED_CACHE_DIRECTORY_DELAY_SECONDS: float = 5 * 60.0
    SEED_CACHE_FILE_DELAY_SECONDS: float = 1 * 60.0
    # Query database for some possibly useful phrases. Need to research
    # efficacy.
    SEED_CACHE_ADD_MOVIE_INFO: bool = False
    SEED_CACHE_MOVIE_INFO_START_DELAY_SECONDS: float = 6 * 60.0
    SEED_CACHE_MOVIE_INFO_DELAY_BETWEEN_QUERY_SECONDS: float = 10.0

    @staticmethod
    def static_init() -> None:
        """
            Assign calculated values

        :return:
        """
        Constants.ADDON = addon.addon
        Constants.ADDON_DATA = addon.DATA_PATH
        Constants.USER_DATA_PATH = Path(xbmcvfs.translatePath("special://userdata"))
        Constants.RESOURCES_PATH = addon.PATH / 'resources'
        Constants.PYTHON_ROOT_PATH = Constants.RESOURCES_PATH / 'lib'

        Constants.ADDON_DIRECTORY = Path(xbmcvfs.translatePath(str(addon.PATH)))
        Constants.ADDON_PATH = addon.PATH
        Constants.BACKENDS_DIRECTORY = Constants.PYTHON_ROOT_PATH / 'backends'
        Constants.CONFIG_SCRIPTS_DIR_WINDOWS = (Path(Constants.RESOURCES_PATH)
                                                / 'scripts')
        Constants.CONFIG_SCRIPT_PATH_WINDOWS = Path(Constants.ADDON_PATH,
                                                    'config_script.bat')
        Constants.DISABLE_PATH = addon.DATA_PATH / 'DISABLED'
        Constants.DEFAULT_CACHE_DIRECTORY = Path(Constants.ADDON_DATA, 'cache')
        Constants.ESPEAK_DATA_PATH_LINUX = (
            Path('/usr/lib/x86_64-linux-gnu/espeak-ng-data'))
        Constants.ESPEAK_DATA_PATH_WINDOWS = (
            Path(r'C:/Program Files/eSpeak NG/espeak-ng-data'))
        # Constants.ESPEAK_PATH_LINUX = Path('/usr/bin/espeak-ng')
        Constants.ESPEAK_PATH_WINDOWS = Path(r'C:/Program Files/eSpeak NG/espeak-ng.exe')
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
        if Constants.PLATFORM_WINDOWS:
            lang_country: str = xbmc.getLanguage(xbmc.ISO_639_1, True)
            Constants.LOCALE = lang_country.lower().replace('_', '-')

            espeak_path: Path = Constants.ESPEAK_PATH_WINDOWS
            if not espeak_path.exists():
                if DEBUG_LOGGING:
                    xbmc.log(f'espeak-ng.exe not found in default path: {espeak_path}.')
                espeak_path = Path(os.environ.get('ESPEAK_PATH', ''))
                if not espeak_path.exists():
                    if DEBUG_LOGGING:
                        xbmc.log(f'ESPEAK_PATH env variable not found or invalid: '
                                 f'{espeak_path}')
            else:
                Constants.ESPEAK_PATH = espeak_path
            espeak_data_path: Path = Constants.ESPEAK_DATA_PATH_WINDOWS
            if not espeak_data_path.exists():
                if DEBUG_LOGGING:
                    xbmc.log(f'Predefined espeak data path not found: {espeak_data_path}')
                espeak_data_path = Path(os.environ.get('ESPEAK_DATA_PATH', ''))
                if not espeak_data_path.exists():
                    if DEBUG_LOGGING:
                        xbmc.log(f'ESPEAK_DATA_PATH env variable not found or invalid: '
                                 f'{espeak_data_path}')
            else:
                Constants.ESPEAK_DATA_PATH = espeak_data_path

            mpv_dir: str = Constants.MPV_PATH_WINDOWS
            if not Path(mpv_dir).exists():
                if DEBUG_LOGGING:
                    xbmc.log(msg=f'Default mpv path of {mpv_dir} is incorrect, '
                                 f'falling back to MPV_PATH env var')
                mpv_dir = os.environ.get('MPV_PATH', '')
                if not Path(mpv_dir).exists():
                    if DEBUG_LOGGING:
                        xbmc.log(msg=f'Can not find mpv on MPV_PATH env var: '
                                 '{mpv_dir}')
            if Path(mpv_dir).exists():
                Constants.MPV_PATH = Constants.MPV_PATH_WINDOWS

            mplayer_dir: str = Constants.MPLAYER_PATH_WINDOWS
            if not Path(mplayer_dir).exists():
                if DEBUG_LOGGING:
                    xbmc.log(msg=f'Default mplayer path of {mplayer_dir} is incorrect, '
                                 f'falling back to MPLAYER_PATH env var')
            mplayer_dir: str = os.environ.get('MPLAYER_PATH', '')
            if not Path(mplayer_dir).exists():
                if DEBUG_LOGGING:
                    xbmc.log(f'mplayer_path: {mplayer_dir} does NOT exist.',
                             xbmc.LOGDEBUG)
            else:
                Constants.MPLAYER_PATH = str(Path(mplayer_dir))
        else:
            lang_country, _ = locale.getlocale()
            lang_country: str
            Constants.LOCALE = lang_country.lower().replace('_', '-')
            Constants.MPV_PATH = Constants.MPV_PATH_LINUX
            Constants.MPLAYER_PATH = Constants.MPLAYER_PATH_LINUX
            Constants.ESPEAK_PATH = Constants.ESPEAK_PATH_LINUX
            Constants.ESPEAK_COMMAND = Constants.ESPEAK_COMMAND_LINUX
            Constants.ESPEAK_DATA_PATH = Constants.ESPEAK_DATA_PATH_LINUX

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
