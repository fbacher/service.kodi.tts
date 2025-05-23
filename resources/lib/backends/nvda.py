# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes
import os
import sys

from common import *

from common.configuration_utils import ConfigUtils
from common.constants import Constants
from common.logger import *
from .base import BaseEngineService

module_logger = BasicLogger.get_logger(__name__)


def getDLLPath():
    p = os.path.join(Constants.PROFILE_PATH, 'nvdaControllerClient32.dll')
    if os.path.exists(p):
        return p
    p = os.path.join(Constants.BACKENDS_DIRECTORY, 'nvda', 'nvdaControllerClient32.dll')
    if os.path.exists(p):
        return p
    try:
        import xbmc
        if xbmc.getCondVisibility('System.HasAddon(script.module.nvdacontrollerclient)'):
            import xbmcaddon
            nvdaCCAddon = xbmcaddon.Addon('script.module.nvdacontrollerclient')
            p = os.path.join(nvdaCCAddon.getAddonInfo('path'), 'nvda',
                             'nvdaControllerClient32.dll')
            if os.path.exists(p):
                return p
    except (ImportError, AttributeError):
        return None
    return None


try:
    from ctypes import windll
except ImportError:
    windll = None


class NVDATTSBackend(BaseEngineService):
    engine_id = 'nvda'
    displayName = 'NVDA'
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger

    @staticmethod
    def available():
        dllPath = getDLLPath()
        if not dllPath or not windll:
            return False
        try:
            dll = ctypes.windll.LoadLibrary(dllPath)
            res = dll.nvdaController_testIfRunning() == 0
            ctypes.windll.kernel32.FreeLibrary(dll._handle)
            del dll
            return res
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False

    def init(self):
        try:
            self.dll = ctypes.windll.LoadLibrary(getDLLPath())
        except AbortException:
            reraise(*sys.exc_info())
        except:
            self.dll = None

    @staticmethod
    def isSupportedOnPlatform():
        return ConfigUtils.isWindows()

    @staticmethod
    def isInstalled():
        installed = False
        if NVDATTSBackend.isSupportedOnPlatform():
            installed = NVDATTSBackend.available()

        return installed

    def isRunning(self):
        return self.dll.nvdaController_testIfRunning() == 0

    def say(self, text, interrupt=False, preload_cache=False):
        if not self.dll:
            return

        if interrupt:
            self.stop()
        if not self.dll.nvdaController_speakText(text) == 0:
            if not self.isRunning():
                self.flagAsDead('Not running')
                return

    def sayList(self, texts, interrupt=False):
        self.say('\n'.join(texts), interrupt)

    def stop(self):
        if not self.dll:
            return
        self.dll.nvdaController_cancelSpeech()

    def close(self):
        if not self.dll:
            return
        ctypes.windll.kernel32.FreeLibrary(self.dll._handle)
        del self.dll
        self.dll = None
