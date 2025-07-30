# coding=utf-8

"""
Utilities with very few external dependencies.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List
from json import JSONEncoder
import json as json
import xbmc
import xbmcaddon
import xbmcvfs

from common import AbortException
from common.critical_settings import CriticalSettings


monitor: xbmc.Monitor = xbmc.Monitor()


class UtilsLowLevel:

    notification_callback: Callable[[List[str], bool], None] = None

    @staticmethod
    def reg_voice_notification_callback(callback:
                                        Callable[[List[str], bool], None]) -> None:
        UtilsLowLevel.notification_callback = callback

    @staticmethod
    def notifySayText(text: List[str] | str, interrupt: bool = False):
        """
        Voices the given text using an ineffcient means, but with minimal dependencies.
        """
        if isinstance(text, str):
            text = [text]
        xbmc.log(f'NotifySayText: {text}')
        if UtilsLowLevel.notification_callback is None:
            raise ValueError(f'UtilsLowLevel.notification_callback is not set')
        UtilsLowLevel.notification_callback(text, interrupt)

    @staticmethod
    def show_and_say_notification(message: str, time_s: float = 3.0,
                                  icon_path: str | None = None,
                                  header: str = CriticalSettings.ADDON_ID,
                                  block: bool = True):
        """
        Displays a Kodi Notification dialog as well as voicing the text.
        :param message: The message to display and voice
        :param time_s: The time in seconds to display the message
        :param icon_path: Path to an icon to display along with the message
        :param header: A header to display and voice along with the message.
                       The default message is kodi TTS's addon id
        :param block: If True, then don't return until time_s seconds has
                      elapsed. This helps to keep the voicing from being
                      clobbered.
        """
        try:
            icon_path = icon_path or xbmcvfs.translatePath(
                    xbmcaddon.Addon(CriticalSettings.ADDON_ID).getAddonInfo('icon'))
            time_ms: int = int(1000.0 * time_s)
            #  notifySayText(text='Notification: {header}. {message}')
            msg: str = f'Notification("{header}","{message}",{time_ms},"{icon_path}")'
            xbmc.log(f'utils_ll Notification: {msg} timeout={time_s}')
            text: str = header
            if header != '' and header[-1] != '.':
                header = f'{header}.'
            if message != '' and message[-1] != '.':
                message = f'{message}.'

            xbmc.executebuiltin(f'Notification({header},{message},{time_ms},{icon_path})')
            UtilsLowLevel.notifySayText(f'{header} {message}')
            if block:
                monitor.waitForAbort(timeout=time_s)
        except AbortException:
            pass
        except RuntimeError:  # Happens when disabling the addon
            pass
