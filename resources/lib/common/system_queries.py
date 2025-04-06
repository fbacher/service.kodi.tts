# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os

import xbmc
import xbmcvfs

from common import *

from common.constants import Constants
from common.logger import *

module_logger = BasicLogger.get_logger(__name__)


class SystemQueries:
    _logger = None
    is_windows: bool | None = None
    is_android: bool | None = None
    is_osx: bool | None = None

    def __init__(self):
        SystemQueries._logger = module_logger

    @classmethod
    def isWindows(cls):
        if cls.is_windows is None:
            cls.is_windows = xbmc.getCondVisibility('System.Platform.Windows')
        return cls.is_windows

    @classmethod
    def isOSX(cls):
        if cls.is_osx is None:
            cls.is_osx = xbmc.getCondVisibility('System.Platform.OSX')
        return cls.is_osx

    @classmethod
    def isAndroid(cls):
        if cls.is_android is None:
            cls.is_android = xbmc.getCondVisibility('System.Platform.Android')
        return cls.is_android

    @classmethod
    def isATV2(cls):
        return xbmc.getCondVisibility('System.Platform.ATV2')

    @classmethod
    def isRaspberryPi(cls):
        return xbmc.getCondVisibility('System.Platform.Linux')

    @classmethod
    def isLinux(cls):
        return xbmc.getCondVisibility('System.Platform.Linux')

    @classmethod
    def raspberryPiDistro(cls):
        if not cls.isRaspberryPi():
            return None
        if cls.isOpenElec():
            return 'OPENELEC'
        uname = None
        import subprocess
        try:
            if Constants.PLATFORM_WINDOWS:
                MY_LOGGER.info(f'Running command:')
                uname = subprocess.check_output(
                            ['uname', '-a'], text=True, shell=False,
                            close_fds=True, creationflags=subprocess.DETACHED_PROCESS)
            else:
                MY_LOGGER.info(f'Running command:')
                uname = subprocess.check_output(['uname', '-a'], text=True,
                                                shell=False, close_fds=True)
        except:
            module_logger.error('raspberryPiDistro() - Failed to get uname output')
        if uname and 'raspbmc' in uname:
            return 'RASPBMC'
        return 'UNKNOWN'

    @classmethod
    def isOpenElec(cls):
        return xbmc.getCondVisibility('System.HasAddon(os.openelec.tv)')

    @classmethod
    def isPreInstalled(cls):
        kodiPath = xbmcvfs.translatePath('special://xbmc')
        preInstalledPath = os.path.join(kodiPath, 'addons', Constants.ADDON_ID)
        return os.path.exists(preInstalledPath)

    @classmethod
    def wasPostInstalled(cls):
        if os.path.exists(Constants.DISABLE_PATH):
            with open(Constants.DISABLE_PATH, 'rt', encoding='utf-8') as f:
                return f.read() == 'POST'
        elif os.path.exists(Constants.ENABLE_PATH):
            with open(Constants.ENABLE_PATH, 'rt', encoding='utf-8') as f:
                return f.read() == 'POST'

        return False

    @classmethod
    def wasPreInstalled(cls):
        if os.path.exists(Constants.DISABLE_PATH):
            with open(Constants.DISABLE_PATH, 'rt', encoding='utf-8') as f:
                return f.read() == 'PRE'
        elif os.path.exists(Constants.ENABLE_PATH):
            with open(Constants.ENABLE_PATH, 'rt', encoding='utf-8') as f:
                return f.read() == 'PRE'

        return False

    @classmethod
    def commandIsAvailable(cls, command):
        for p in os.environ["PATH"].split(os.pathsep):
            if os.path.isfile(os.path.join(p, command)):
                return True
        return False


instance = SystemQueries()  # Initialize get
