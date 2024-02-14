from __future__ import annotations  # For union operator |

import os
import sys
from pathlib import Path

import xbmc

from common import *

from common.constants import Constants
from common.monitor import Monitor

BASE_COMMAND = ('XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",'
                '\\"interrupt\\":{1}}}")')
XT = xbmc.getLocalizedString


def tailXBMCLog(num_lines=10):
    with open(Constants.LOG_PATH, "rt", encoding='utf-8') as f:
        f.seek(0, 2)
        fsize = f.tell()
        f.seek(max(fsize - 1024, 0), 0)
        lines = f.readlines()
    return lines[-num_lines:]


def getTmpfs(subdir: str = None):
    if sys.platform.startswith('win'):
        return None
    temp_path: str = None
    for temp_path in ('/run/shm', '/dev/shm', '/tmp'):
        if os.path.exists(temp_path):
            break
    if temp_path is not None:
        temp_path: Path = Path(temp_path)
        if subdir:
            temp_path = temp_path / subdir
        return str(temp_path)
    return None


def sleep(ms):
    seconds: float = ms / 1000.0
    Monitor.exception_on_abort(timeout=seconds)


def playSound(name, return_duration=False):
    wavPath = os.path.join(Constants.ADDON_DIRECTORY, 'resources',
                           'wavs', '{0}.wav'.format(name))
    # This doesn't work as this may be called when the addon is disabled
    # wavPath = os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo(
    # 'path')),'resources','wavs','{0}.wav'.format(name))
    xbmc.playSFX(wavPath)
    if return_duration:
        wavPath = wavPath
        if not os.path.exists(wavPath):
            return 0
        import wave
        w = wave.open(wavPath, 'rb')
        frames = w.getnframes()
        rate = w.getframerate()
        w.close()
        duration = frames / float(rate)
        return duration


def stopSounds():
    if hasattr(xbmc, 'stopSFX'):
        xbmc.stopSFX()


def notifySayText(text, interrupt=False):
    command = BASE_COMMAND.format(text, repr(interrupt).lower())
    # print command
    xbmc.executebuiltin(command)
