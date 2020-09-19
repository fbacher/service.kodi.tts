# -*- coding: utf-8 -*-

import sys

from backends.base import SimpleTTSBackendBase

from common.constants import Constants
from common.logger import LazyLogger
from common.system_queries import SystemQueries
from common.messages import Messages
from common.setting_constants import Languages, Genders, Players
from common.settings import Settings
from .base import ThreadedTTSBackend


module_logger = LazyLogger.get_addon_module_logger(file_path=__file__)


class JAWSTTSBackend(ThreadedTTSBackend):
    provider = 'JAWS'
    displayName = 'JAWS'
    interval = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = module_logger.getChild(self.__class__.__name__)  # type: LazyLogger
        self.jaws = None

    def init(self):
        from comtypes import client
        try:
            self.jaws = client.CreateObject('FreedomSci.JawsApi')
        except:
            self.jaws = client.CreateObject('jfwapi')

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isWindows()

    @staticmethod
    def isInstalled():
        installed = False

        if JAWSTTSBackend.isSupportedOnPlatform():
            instance = JAWSTTSBackend()
            installed = instance.jaws
        return installed

    def threadedSay(self, text):
        if not self.jaws: return
        if not self.jaws.SayString(text,False): self.flagAsDead('Not running')

    def stop(self):
        if not self.jaws: return
        self.jaws.StopSpeech()

    def isSpeaking(self):
        return ThreadedTTSBackend.isSpeaking(self) or None

    def close(self):
        del self.jaws
        self.jaws = None

    @staticmethod
    def available():
        if not sys.platform.lower().startswith('win'): return False
        try:
            from comtypes import GUID
            GUID.from_progid('FreedomSci.JawsApi') #If we fail on this, we haven't loaded anything
            from comtypes.client import CreateObject
            test = CreateObject("FreedomSci.JawsApi")
            return test.SayString("",False)
        except:
            return False
        return True