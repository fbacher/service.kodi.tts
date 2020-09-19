# -*- coding: utf-8 -*-

import os

import xbmc
import xbmcvfs

from common.constants import Constants
from common.logger import LazyLogger

module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class SystemQueries:
    _logger = None

    def __init__(self):
        SystemQueries._logger = module_logger.getChild(
            self.__class__.__name__)  # type: LazyLogger

    @classmethod
    def isWindows(cls):
        return xbmc.getCondVisibility('System.Platform.Windows')

    @classmethod
    def isOSX(cls):
        return xbmc.getCondVisibility('System.Platform.OSX')


    @classmethod
    def isAndroid(cls):
        return xbmc.getCondVisibility('System.Platform.Android')


    @classmethod
    def isATV2(cls):
        return xbmc.getCondVisibility('System.Platform.ATV2')


    @classmethod
    def isRaspberryPi(cls):
        return xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi')


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
            uname = subprocess.check_output(
                ['uname', '-a'], universal_newlines=True)
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
            with open(Constants.DISABLE_PATH, 'r') as f:
                return f.read() == 'POST'
        elif os.path.exists(Constants.ENABLE_PATH):
            with open(Constants.ENABLE_PATH, 'r') as f:
                return f.read() == 'POST'

        return False

    @classmethod
    def wasPreInstalled(cls):
        if os.path.exists(Constants.DISABLE_PATH):
            with open(Constants.DISABLE_PATH, 'r') as f:
                return f.read() == 'PRE'
        elif os.path.exists(Constants.ENABLE_PATH):
            with open(Constants.ENABLE_PATH, 'r') as f:
                return f.read() == 'PRE'

        return False

    @classmethod
    def commandIsAvailable(cls, command):
        for p in os.environ["PATH"].split(os.pathsep):
            if os.path.isfile(os.path.join(p, command)):
                return True
        return False


instance = SystemQueries()  # Initialize logger