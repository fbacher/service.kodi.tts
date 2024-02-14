# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

from common import *

from common import utils
from common.constants import Constants
from common.logger import *
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from backends.base import ThreadedTTSBackend
from backends.settings.constraints import Constraints

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class OSXSayTTSBackend_Internal(ThreadedTTSBackend):
    backend_id = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True
    volumeConstraints: Constraints = Constraints(0, 100, 100, True, False, 1.0,
                                                 SettingsProperties.VOLUME)
    speedConstraints: Constraints = Constraints(80, 200, 450, True, False, 1.0,
                                                SettingsProperties.SPEED, 0)

    volumeExternalEndpoints = (0, 100)
    volumeStep = 5
    volumeSuffix = '%'
    voicesPath = os.path.join(Constants.PROFILE_PATH, f'{backend_id}.voices')
    settings = {
        SettingsProperties.SPEED : 0,
        SettingsProperties.VOICE : '',
        SettingsProperties.VOLUME: 100
    }

    #  def __new__(cls):
    #      try:
    #          import xbmc #analysis:ignore
    #          return super().__new__()
    #      except:
    #          pass
    #      return # OSXSayTTSBackend_SubProcess() #  TODO: does not exist!
    _logger_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._logger_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._logger_name)

        from . import cocoapy
        self.cocoapy = cocoapy
        self.pool = cocoapy.ObjCClass('NSAutoreleasePool').alloc().init()
        self.synth = cocoapy.ObjCClass('NSSpeechSynthesizer').alloc().init()
        voices = self.longVoices()
        self.saveVoices(voices)  # Save the voices to file, so we can get provide them
        # for selection without initializing the synth again
        self.update()

    def threadedSay(self, text):
        if not text:
            return
        self.synth.startSpeakingString_(self.cocoapy.get_NSString(text))
        while self.synth.isSpeaking():
            utils.sleep(10)

    def getWavStream(self, text):
        wav_path = os.path.join(utils.getTmpfs(), 'speech.wav')
        subprocess.call(['say', '-o', wav_path,
                         '--file-format', 'WAVE', '--data-format', 'LEI16@22050', text],
                        universal_newlines=True)
        return open(wav_path, 'rb')

    def isSpeaking(self):
        return self.synth.isSpeaking()

    def longVoices(self):
        vNSCFArray = self.synth.availableVoices()
        voices = [self.cocoapy.cfstring_to_string(
                vNSCFArray.objectAtIndex_(i, self.cocoapy.get_NSString('UTF8String')))
            for i in range(vNSCFArray.count())]
        return voices

    def update(self):
        self.voice: str = self.setting(SettingsProperties.VOICE)
        self.volume: float = self.setting(SettingsProperties.VOLUME) / 100.0
        self.rate = self.setting(SettingsProperties.SPEED)
        if self.voice:
            self.synth.setVoice_(self.cocoapy.get_NSString(self.voice))
        if self.volume:
            self.synth.setVolume_(self.volume)
        if self.rate:
            self.synth.setRate_(self.rate)

    def stop(self):
        self.synth.stopSpeaking()

    def close(self):
        self.pool.release()

    @classmethod
    def settingList(cls, setting, *args):
        if setting == SettingsProperties.VOICE:
            lvoices = cls.loadVoices()
            if not lvoices:
                return None
            voices = [(v, v.rsplit('.', 1)[-1]) for v in lvoices]
            return voices

    @classmethod
    def saveVoices(cls, voices):
        if not voices:
            return
        out = '\n'.join(voices)
        with open(cls.voicesPath, 'w', encoding='utf-8') as f:
            f.write(out)

    @classmethod
    def loadVoices(cls):
        if not os.path.exists(cls.voicesPath):
            return None
        with open(cls.voicesPath, 'r', encoding='utf-8') as f:
            return f.read().splitlines()

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not SystemQueries.isATV2()


# OLD
class OSXSayTTSBackend(ThreadedTTSBackend):
    backend_id = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True
    _logger_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._logger_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._logger_name)
        self.process = None

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isOSX()

    @staticmethod
    def isInstalled():
        return OSXSayTTSBackend.isSupportedOnPlatform()

    def threadedSay(self, text):
        if not text:
            return
        self.process = subprocess.Popen(['say', text], universal_newlines=True,
                                        encoding='utf-8')
        while self.process.poll() is None and self.active:
            utils.sleep(10)

    def getWavStream(self, text):
        wav_path = os.path.join(utils.getTmpfs(), 'speech.wav')
        subprocess.call(['say', '-o', wav_path,
                         '--file-format', 'WAVE', '--data-format', 'LEI16@22050',
                         text], universal_newlines=True)
        return open(wav_path, 'rb')

    def isSpeaking(self):
        return (
                self.process and self.process.poll() is None) or \
            ThreadedTTSBackend.isSpeaking(
                    self)

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
        return sys.platform == 'darwin' and not SystemQueries.isATV2()
