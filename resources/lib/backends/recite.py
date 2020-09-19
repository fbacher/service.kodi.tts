# -*- coding: utf-8 -*-
from . import base
import subprocess
import os
from typing import Any, List, Union, Type

from backends.audio import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase
from backends import base
from backends.audio import BuiltInAudioPlayer, BuiltInAudioPlayerHandler
from common.constants import Constants
from common.setting_constants import Backends, Languages, Players, Genders, Misc
from common.logger import LazyLogger
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries
from common import utils


module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class ReciteTTSBackend(base.SimpleTTSBackendBase):
    """
     reciteme.com/
    """
    provider = Backends.RECITE_ID
    displayName = 'Recite'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: LazyLogger

    def init(self):
        self.process = None

    def runCommandAndSpeak(self,text):
        args = ['recite',text]
        self.process = subprocess.Popen(args, universal_newlines=True)
        while self.process.poll() is None and self.active: utils.sleep(10)

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux() or SystemQueries.isWindows() or SystemQueries.isOSX()

    @staticmethod
    def isInstalled():
        installed = False
        if ReciteTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @staticmethod
    def available():
        try:
            subprocess.call(['recite','-VERSion'], stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except:
            return False
        return True

