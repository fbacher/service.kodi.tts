import os
import sys

import xbmc

from common.constants import Constants

BASE_COMMAND = ('XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",'
                '\\"interrupt\\":{1}}}")')
XT = xbmc.getLocalizedString


def tailXBMCLog(num_lines=10):
    with open(Constants.LOG_PATH, "r") as f:
        f.seek(0, 2)
        fsize = f.tell()
        f.seek(max(fsize - 1024, 0), 0)
        lines = f.readlines()
    return lines[-num_lines:]


def getTmpfs():
    if sys.platform.startswith('win'):
        return None
    for tmpfs in ('/run/shm', '/dev/shm', '/tmp'):
        if os.path.exists(tmpfs):
            return tmpfs
    return None


def sleep(ms):
    xbmc.sleep(ms)


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
