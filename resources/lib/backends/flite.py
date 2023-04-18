# -*- coding: utf-8 -*-
import os, subprocess
import xbmc

from typing import Any, List, Union, Type

from backends.audio import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase
from backends import base
from backends.audio import BuiltInAudioPlayer, BuiltInAudioPlayerHandler
from common.constants import Constants
from common.setting_constants import Backends, Languages, Players, Genders, Misc
from common.logger import *
from common.messages import Messages
from common.settings import Settings
from common.system_queries import SystemQueries

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class FliteTTSBackend(base.SimpleTTSBackendBase):
    backend_id = Backends.FLITE_ID
    displayName = 'Flite'
    speedConstraints = (20, 100, 200, True)

    settings = {
        Settings.PIPE: False,
                Settings.PLAYER: Players.INTERNAL,
                Settings.SPEED: 100,
                Settings.VOICE: 'kal16',
        Settings.VOLUME: 0
    }
    onATV2 = SystemQueries.isATV2()

    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)
        self.process = None

    def init(self):
        self.process = None
        self.update()

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux()

    @staticmethod
    def isInstalled():
        installed = False
        if FliteTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def runCommand(self,text_to_voice,dummy):
        wave_file, exists = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=False)

        if self.onATV2:
            os.system('flite -t "{0}" -o "{1}"'.format(text_to_voice,wave_file))
        else:
            voice = type(self).getVoice()
            subprocess.call(['flite', '-voice', voice, '-t', text_to_voice,'-o',wave_file],
                            universal_newlines=True)
        return True

    def runCommandAndSpeak(self,text_to_voice):

        voice = type(self).getVoice()
        self.process = subprocess.Popen(['flite', '-voice', voice, '-t', text_to_voice],
                                        universal_newlines=True)
        while self.process.poll() is None and self.active: xbmc.sleep(10)

    def update(self):
        pass

    def getMode(self):
        if not self.onATV2 and self.setting('output_via_flite'):
            return base.SimpleTTSBackendBase.ENGINESPEAK
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @classmethod
    def settingList(cls,setting,*args):
        if cls.onATV2:
            return None

        elif setting == Settings.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(Settings.PLAYER)

            return players, default_player

        elif setting == 'voice':
            return [(v,v) for v in subprocess.check_output(['flite','-lv'],
                                                           universal_newlines=True).split(': ',1)[-1].strip().split(' ')]

    @staticmethod
    def available():
        try:
            subprocess.call(['flite', '--help'], stdout=(open(os.path.devnull, 'w')),
                            universal_newlines=True, stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return SystemQueries.isATV2() and SystemQueries.commandIsAvailable('flite')
        return True

#class FliteTTSBackend(TTSBackendBase):
#    backend_id = 'Flite':q:q
#    def __init__(self):
#        import ctypes
#        self.flite = ctypes.CDLL('libflite.so.1',mode=ctypes.RTLD_GLOBAL)
#        flite_usenglish = ctypes.CDLL('libflite_usenglish.so.1',mode=ctypes.RTLD_GLOBAL) #analysis:ignore
#        flite_cmulex = ctypes.CDLL('libflite_cmulex.so.1',mode=ctypes.RTLD_GLOBAL) #analysis:ignore
#        flite_cmu_us_slt = ctypes.CDLL('libflite_cmu_us_slt.so.1')
#        self.flite.flite_init()
#        self.voice = flite_cmu_us_slt.register_cmu_us_slt()
#
#    def say(self,text,interrupt=False):
#        if not text: return
#        self.flite.flite_text_to_speech(text,self.voice,'play')
#
#
#    @staticmethod
#    def available():
#        try:
#            import ctypes
#            ctypes.CDLL('libflite.so.1')
#        except (OSError, IOError):
#            return False
#        return True

#class FliteTTSBackend(TTSBackendBase):
#    backend_id = 'Flite'
#
#    def say(self,text,interrupt=False):
#        if not text: return
#        voice = self.currentVoice() or 'kal16'
#        subprocess.call(['flite', '-voice', voice, '-t', text], universal_newlines=True)
#
#    def voices(self):
#        return subprocess.check_output(['flite','-lv'], universal_newlines=True).split(': ',1)[-1].strip().split(' ')
#
#    @staticmethod
#    def available():
#        try:
#            subprocess.call(['flite', '--help'], stdout=(open(os.path.devnull, 'w')),
#            stderr=subprocess.STDOUT, universal_newlines=True)
#        except (OSError, IOError):
#            return False
#        return True
