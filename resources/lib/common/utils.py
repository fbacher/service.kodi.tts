# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import sys
from pathlib import Path

import xbmc

from common import *

from common.constants import Constants
from common.logger import *
from common.monitor import Monitor

BASE_COMMAND = ('XBMC.NotifyAll(service.kodi.tts,SAY,"{{\\"text\\":\\"{0}\\",'
                '\\"interrupt\\":{1}}}")')
XT = xbmc.getLocalizedString

MY_LOGGER = BasicLogger.get_logger(__name__)


def tailXBMCLog(num_lines=10):
    with open(Constants.LOG_PATH, "rt", encoding='utf-8') as f:
        f.seek(0, 2)
        fsize = f.tell()
        f.seek(max(fsize - 1024, 0), 0)
        lines = f.readlines()
    return lines[-num_lines:]


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


class TempFileUtils:

    tmp_dir: Path | None = None

    @classmethod
    def getTmpfs(cls) -> Path | None:
        """
        Returns the default directory for temporary files.
        :return:
        """
        if sys.platform.startswith('win'):
            return None
        temp_path: Path
        for tmp_dir in ('/run/shm', '/dev/shm', '/tmp'):
            tmp_dir: str
            temp_path = Path(tmp_dir)
            if temp_path.exists():
                break
        return temp_path

    @classmethod
    def temp_dir(cls) -> Path:
        """
        Controls the tempfile and tempfile.NamedTemporaryFile 'dir' entry
        used to create temporary audio files. A None value allows tempfile
        to decide.
        :return:
        """
        if cls.tmp_dir is None:
            tmpfs: Path | None = None
            tmpfs = cls.getTmpfs()
            if tmpfs is None:
                tmpfs = Path(Constants.PROFILE_PATH)
            tmpfs = tmpfs / 'kodi_speech'
            if tmpfs.exists():
                cls.clean_tmp_dir(tmpfs)
            tmpfs.mkdir(mode=0o777, parents=True, exist_ok=True)
            cls.tmp_dir = tmpfs
        return cls.tmp_dir

    @classmethod
    def clean_tmp_dir(cls, tmp_dir: Path) -> None:
        """
        Remove all files and directories from tmp_dir

        :param tmp_dir:
        :return:
        """
        try:
            dirs_to_delete: List[Path] = []
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'tmp_dir: {tmp_dir}')
            if not tmp_dir.exists():
                tmp_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                return
            if not tmp_dir.is_dir():
                tmp_dir.unlink(missing_ok=True)
                tmp_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                return
            for child in tmp_dir.iterdir():
                child: Path
                try:
                    if child.is_dir():
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'dir: {child}')
                        dirs_to_delete.append(child)
                        continue
                    if child.is_file():
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'unlink file: {child}')
                        child.unlink(missing_ok=True)
                except:
                    MY_LOGGER.exception('')
            deleted_dirs: List[Path] = []
            for child in dirs_to_delete:
                child: Path
                try:
                    if not child.is_dir() and MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Expected to be directory: {child}')
                    else:
                        cls.clean_tmp_dir(child)
                        child.rmdir()
                        deleted_dirs.append(child)
                except:
                    MY_LOGGER.exception('')
            for child in deleted_dirs:
                dirs_to_delete.remove(child)
            if len(dirs_to_delete) > 0:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Could not delete {len(dirs_to_delete)} directories')
        except:
            MY_LOGGER.exception('')
