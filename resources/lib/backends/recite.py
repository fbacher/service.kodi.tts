# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from backends import base
from common import utils
from common.logger import *
from common.setting_constants import Backends
from common.system_queries import SystemQueries

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ReciteTTSBackend(base.SimpleTTSBackend):
    """
     reciteme.com/
    """
    backend_id = Backends.RECITE_ID
    displayName = 'Recite'
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)

    def init(self):
        self.process = None

    def runCommandAndSpeak(self, text):
        args = ['recite', text]
        self.process = subprocess.Popen(args, universal_newlines=True, encoding='utf-8')
        while self.process.poll() is None and self.active:
            utils.sleep(10)

    @staticmethod
    def isSupportedOnPlatform():
        return (SystemQueries.isLinux() or SystemQueries.isWindows() or
                SystemQueries.isOSX())

    @staticmethod
    def isInstalled():
        installed = False
        if ReciteTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def stop(self):
        if not self.process:
            return
        try:
            self.process.terminate()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @staticmethod
    def available():
        try:
            subprocess.call(['recite', '-VERSion'],
                            stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True,
                            encoding='utf-8')
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return False
        return True
