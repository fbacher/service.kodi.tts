# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess
import sys

import xbmc

from common import *

from backends.base import SimpleTTSBackend
from common.logger import *
from common.monitor import Monitor
from common.setting_constants import Backends, Mode, Players
from common.settings_low_level import SettingProp
from common.system_queries import SystemQueries

module_logger: BasicLogger = BasicLogger.get_logger(__name__)


class FliteTTSBackend(SimpleTTSBackend):
    engine_id = Backends.FLITE_ID
    displayName = 'Flite'
    #  speedConstraints = (20, 100, 200, True)

    settings = {
        SettingProp.PIPE  : False,
        SettingProp.PLAYER: Players.BUILT_IN,
        SettingProp.SPEED : 100,
        SettingProp.VOICE : 'kal16',
        SettingProp.VOLUME: 0
    }
    onATV2 = SystemQueries.isATV2()

    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super().__init__(*args, **kwargs)
        clz._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger
        if not clz._initialized:
            clz._initialized = True
            self.register(self)
        self.process = None

    def init(self):
        self.process = None
        self.update()

    def runCommand(self, text_to_voice: str, dummy) -> bool:
        wave_file, exists = self.get_path_to_voice_file(text_to_voice,
                                                        use_cache=False)

        if self.onATV2:
            os.system('flite -t "{0}" -o "{1}"'.format(text_to_voice, wave_file))
        else:
            voice = type(self).getVoice()
            subprocess.call(
                    ['flite', '-voice', voice, '-t', text_to_voice, '-o', wave_file],
                    universal_newlines=True)
        return True

    def runCommandAndSpeak(self, text_to_voice: str) -> None:
        clz = type(self)
        voice = type(self).getVoice()
        self.process = subprocess.Popen(['flite', '-voice', voice, '-t', text_to_voice],
                                        universal_newlines=True, encoding='utf-8')
        while self.process.poll() is None and clz.is_active_engine(clz):
            Monitor.exception_on_abort(timeout=0.10)

    def update(self):
        pass

    def getMode(self):
        if not self.onATV2 and self.setting('output_via_flite'):
            return Mode.ENGINESPEAK
        else:
            return Mode.FILEOUT

    def stop(self):
        if not self.process:
            return
        try:
            self.process.terminate()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @classmethod
    def settingList(cls, setting, *args):
        if cls.onATV2:
            return None

        elif setting == SettingProp.PLAYER:
            # Get list of player_key ids. Id is same as is stored in settings.xml

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(SettingProp.PLAYER)

            return players, default_player

        elif setting == SettingProp.VOICE:
            return [(v, v) for v in subprocess.check_output(['flite', '-lv'],
                                                            universal_newlines=True).split(
                ': ', 1)[-1].strip().split(' ')]

# class FliteTTSBackend(BaseEngineService):
#    setting_id = 'Flite':q:q
#    def __init__(self):
#        import ctypes
#        self.flite = ctypes.CDLL('libflite.so.1',mode=ctypes.RTLD_GLOBAL)
#        flite_usenglish = ctypes.CDLL('libflite_usenglish.so.1',
#        mode=ctypes.RTLD_GLOBAL) #analysis:ignore
#        flite_cmulex = ctypes.CDLL('libflite_cmulex.so.1',mode=ctypes.RTLD_GLOBAL)
#        #analysis:ignore
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

# class FliteTTSBackend(BaseEngineService):
#    setting_id = 'Flite'
#
#    def say(self,text,interrupt=False):
#        if not text: return
#        voice = self.currentVoice() or 'kal16'
#        subprocess.call(['flite', '-voice', voice, '-t', text], universal_newlines=True)
#
#    def voices(self):
#        return subprocess.check_output(['flite','-lv'],
#        universal_newlines=True).split(': ',1)[-1].strip().split(' ')
#
#    @staticmethod
#    def available():
#        try:
#            subprocess.call(['flite', '--help'], stdout=(open(os.path.devnull, 'w')),
#            stderr=subprocess.STDOUT, universal_newlines=True)
#        except (OSError, IOError):
#            return False
#        return True
