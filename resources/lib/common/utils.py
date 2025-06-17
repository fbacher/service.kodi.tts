# coding=utf-8
from __future__ import annotations  # For union operator |

import os
import sys
from pathlib import Path
from threading import RLock

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

    single_thread_lock: RLock = RLock()
    tmp_dir: Path | None = None

    @classmethod
    def getTmpfs(cls) -> Path | None:
        """
        Returns the default directory for temporary files.
        :return:
        """
        if sys.platform.startswith('win'):
            return None
        with cls.single_thread_lock:
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
        with cls.single_thread_lock:
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
        with cls.single_thread_lock:
            try:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'tmp_dir: {tmp_dir}')
                if tmp_dir.exists and not tmp_dir.is_dir():
                    try:
                        MY_LOGGER.debug(f'exists, but not a dir. Delete: {tmp_dir}')
                        tmp_dir.unlink(missing_ok=True)
                    except:
                        MY_LOGGER.exception('')
                if not tmp_dir.exists():
                    try:
                        MY_LOGGER.debug(f'dir does not exists, create: {tmp_dir}')
                        tmp_dir.mkdir(mode=0o777, exist_ok=True, parents=True)
                    except:
                        MY_LOGGER.exception('')
                cls.delete_tree(top=tmp_dir)
            except Exception:
                MY_LOGGER.exception('')

    @classmethod
    def delete_tree(cls, top: Path) -> None:
        if not top.is_dir:
            MY_LOGGER.error(f'Expected a dir: {top} exists: {top.exists()}')
        for item in top.iterdir():
            item: Path
            MY_LOGGER.debug(f'item: {item} is_dir: {item.is_dir()}')
            if item.is_dir():
                cls.delete_tree(item)
                try:
                    MY_LOGGER.debug(f'rmdir: {item}')
                    item.rmdir()
                except Exception:
                    MY_LOGGER.exception('')
            else:
                try:
                    MY_LOGGER.debug(f'is_file: {item.is_file()}')
                    item.unlink(missing_ok=True)
                except Exception:
                    MY_LOGGER.exception('')
