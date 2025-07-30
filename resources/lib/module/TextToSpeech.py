# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import xbmcvfs

from common import *

from common.critical_settings import *
from common.minimal_monitor import MinimalMonitor


# def safeEncode(text):
#    return binascii.hexlify(text.encode('utf-8'))

# def safeDecode(enc_text):
#    return binascii.unhexlify(enc_text)


def notifySayText(text: str, interrupt: bool = False):
    """
    Voices the given text using an ineffcient means, but with minimal dependencies.
    """
    command = f'XBMC.NotifyAll(service.kodi.tts,SAY,' \
              f'"{{\\"text\\":\\"{text}\\",\\"interrupt\\":{interrupt}}}")'.lower()
    # print command
    xbmc.executebuiltin(command)


def show_and_say_notification(message: str, time_s: float = 3.0,
                              icon_path: str | None = None,
                              header: str = CriticalSettings.ADDON_ID):
    """
    Wrapper around
    """
    try:
        icon_path = icon_path or xbmcvfs.translatePath(
                xbmcaddon.Addon(CriticalSettings.ADDON_ID).getAddonInfo('icon'))
        time_ms: int = int(1000.0 * time_s)
        notifySayText(text='Notification: {header}. {message}')
        xbmc.executebuiltin(f'Notification({header},{message},{time_ms},{icon_path})')
        MinimalMonitor.real_waitForAbort(time_s)
    except RuntimeError:  # Happens when disabling the addon
        pass

def stop():
    xbmc.executebuiltin(f'XBMC.NotifyAll({CriticalSettings.ADDON_ID}),STOP)')
