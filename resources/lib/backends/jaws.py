# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys

from common import *

from common.logger import *
from common.system_queries import SystemQueries
from .base import ThreadedTTSBackend

module_logger = BasicLogger.get_logger(__name__)


class JAWSTTSBackend(ThreadedTTSBackend):
    engine_id = 'JAWS'
    displayName = 'JAWS'
    interval = 50

    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger
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
        if not self.jaws:
            return
        if not self.jaws.SayString(text, False):
            self.flagAsDead('Not running')

    def stop(self):
        if not self.jaws:
            return
        self.jaws.StopSpeech()

    def isSpeaking(self):
        return ThreadedTTSBackend.isSpeaking(self) or None

    def close(self):
        del self.jaws
        self.jaws = None

    @staticmethod
    def available():
        if not sys.platform.lower().startswith('win'):
            return False
        try:
            from comtypes import GUID
            GUID.from_progid(
                'FreedomSci.JawsApi')  # If we fail on this, we haven't loaded anything
            from comtypes.client import CreateObject
            test = CreateObject("FreedomSci.JawsApi")
            return test.SayString("", False)
        except:
            return False
        return True
