# -*- coding: utf-8 -*-
"""
Created on Feb 10, 2019

@author: Frank Feuerbacher
"""
from pathlib import Path

import xbmc
import xbmcaddon

from common import *

from kutils.kodiaddon import Addon
from .__init__ import *


class CriticalSettings:
    """
        A subset of settings that are used by modules which can not have a
        dependency on Settings.

    """

    # Values based on Python logging

    DISABLED = 0
    FATAL = 50  # logging.CRITICAL
    ERROR = 40  # logging.ERROR  # 40
    WARNING = 30  # logging.WARNING  # 30
    INFO = 20  # logging.INFO  # 20
    DEBUG = 10  # logging.DEBUG  # 10
    DEBUG_VERBOSE = 8
    DEBUG_EXTRA_VERBOSE = 6
    NOTSET = 0  # logging.NOTSET  # 0

    DEFAULT_DEBUG_LEVEL = WARNING
    DEBUG_LOG_LEVEL_SETTING: str = 'debug_log_level.tts'

    POLL_MONITOR_WAIT_FOR_ABORT: bool = True  # False  # If False, wait on abort_event
    SHORT_POLL_DELAY: float = 0.2  # Seconds
    LONG_POLL_DELAY: float = 0.2  # Seconds

    DEBUG_INCLUDE_THREAD_INFO: Final[str] = 'debug_include_thread_info'

    ADDON: xbmcaddon = None
    ADDON_ID: Final[str] = 'service.kodi.tts'  # same as in addon.xml
    ADDON_LOG_NAME: Final[str] = 'tts'  # friendly name for logs
    KODI_SETTINGS: xbmcaddon.Settings = None

    try:
        ADDON = xbmcaddon.Addon(ADDON_ID)
    except Exception:
        xbmc.log(f'xbmcaddon.Addon({ADDON_ID}) was not found.', level=xbmc.LOGERROR)

    ADDON_PATH: Final[Path] = Path(ADDON.getAddonInfo('path'))
    RESOURCES_PATH: Final[Path] = ADDON_PATH.joinpath('resources')
    TOP_PACKAGE_PATH: Final[str] = RESOURCES_PATH.joinpath('lib')
    KODI_SETTINGS = ADDON.getSettings()
    addon = None
    _plugin_name: str = ""
    try:
        addon = Addon(ADDON_ID)
    except Exception:
        xbmc.log(f'{ADDON_ID} not found', level=xbmc.LOGERROR)

    @staticmethod
    def is_debug_enabled() -> bool:
        """

        :return:
        """
        if CriticalSettings.addon is None:
            return False

        debug_enabled = True  # CriticalSettings.KODI_SETTINGS.getBool(DEBUG_LOG_LEVEL_SETTING)
        return debug_enabled

    @staticmethod
    def is_debug_include_thread_info() -> bool:
        """

        :return:
        """
        if CriticalSettings.addon is None:
            return False

        is_debug_include_thread_info = True  # CriticalSettings.KODI_SETTINGS.getBool(
        #        #  CriticalSettings.DEBUG_INCLUDE_THREAD_INFO)
        return bool(is_debug_include_thread_info)
        #        and CriticalSettings.get_logging_level() <= CriticalSettings.DEBUG)

    @staticmethod
    def get_logging_level() -> int:
        """

        :return:
        """
        # level_setting is an enum from settings.xml
        # level_setting 0 -> xbmc.LOGWARNING
        # level_setting 1 => xbmc.LOGINFO
        # level_setting 2 => xbmc.LOGDEBUG
        # level_setting 3 => DEBUG_VERBOSE
        # level_setting 4 => DEBUG_EXTRA_VERBOSE

        # python_logging_value is a transformation to values that Logger uses:
        #
        # Critical is most important.
        # DISABLED is least important
        # DEBUG_EXTRA_VERBOSE less important that DEBUG

        python_logging_value = None

        try:
            # Kodi log values
            # WARNING|INFO|DEBUG|VERBOSE DEBUG|EXTRA VERBOSE DEBUG"

            python_logging_value = CriticalSettings.DEFAULT_DEBUG_LEVEL
            try:
                CriticalSettings.ADDON
            except NameError:
                CriticalSettings.ADDON = None
                xbmc.log('ADDON was not defined.', level=xbmc.LOGDEBUG)

            if CriticalSettings.ADDON is None:
                xbmc.log(f'Can not access {CriticalSettings.ADDON_ID}',
                         level=xbmc.LOGERROR)
                python_logging_value = CriticalSettings.DEFAULT_DEBUG_LEVEL
            elif not CriticalSettings.is_debug_enabled():
                level_setting = 0
                python_logging_value = CriticalSettings.DEFAULT_DEBUG_LEVEL
            else:  # Debug is enabled in Random Trailers Config Experimental Tab
                level_setting: int = CriticalSettings.KODI_SETTINGS.getInt(
                                                CriticalSettings.DEBUG_LOG_LEVEL_SETTING)
                # level_setting = 4
                if level_setting <= 0:  # Use DEFAULT value
                    python_logging_value = CriticalSettings.DEFAULT_DEBUG_LEVEL
                elif level_setting == 1:  # Info
                    python_logging_value = CriticalSettings.INFO
                elif level_setting == 2:  # Debug
                    python_logging_value = CriticalSettings.DEBUG
                elif level_setting == 3:  # Verbose Debug
                    python_logging_value = CriticalSettings.DEBUG_VERBOSE
                elif level_setting >= 4:  # Extra Verbose Debug
                    python_logging_value = CriticalSettings.DEBUG_EXTRA_VERBOSE

                # prefix = '[Thread {!s} {!s}.{!s}:{!s}]'.format(
                # record.threadName, record.name, record.funcName,
                # record.lineno)
                # xbmc.log(f'raw_level: {level_setting} '
                #          f'python_logging_value: {python_logging_value}')
        except Exception:
            xbmc.log('Exception occurred in get_logging_level',
                     level=xbmc.LOGERROR)

        return python_logging_value

    @classmethod
    def get_log_level(cls) -> int:
        level_setting: int = CriticalSettings.KODI_SETTINGS.getInt(
                                                CriticalSettings.DEBUG_LOG_LEVEL_SETTING)
        xbmc.log(f'log_level: {level_setting}')
        return level_setting

    @classmethod
    def set_log_level(cls, level: int) -> None:
        CriticalSettings.KODI_SETTINGS.setInt(CriticalSettings.DEBUG_LOG_LEVEL_SETTING,
                                              level)

    @classmethod
    def set_plugin_name(cls, plugin_name: str):
        """
        Debug-Log friendly name for addon. Since multiple plugins/scripts, etc.
        can exist in an addon, there must be a configurable way to set it at startup.
        It is the responsibility of the app to do this at startup and preferably
        BEFORE import logger.

        """
        cls._plugin_name = plugin_name

    @classmethod
    def get_plugin_name(cls) -> str:
        return cls._plugin_name
