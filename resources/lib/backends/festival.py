# -*- coding: utf-8 -*-
import io
import os, subprocess
from typing import Any, List, Union, Type

from backends.audio import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackendBase
from common.constants import Constants
from common.logger import *
from common.system_queries import SystemQueries
from common.messages import Messages
from common.setting_constants import Backends, Languages, Genders, Players
from common.settings import Settings

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class FestivalTTSBackend(SimpleTTSBackendBase):
    backend_id = Backends.FESTIVAL_ID
    displayName = 'Festival'
    canStreamWav = SystemQueries.commandIsAvailable('mpg123')
    speedConstraints = (-16, 0, 12, True)
    pitchConstraints = (50, 105, 500, True)
    volumeConstraints = (-12, 0, 12, True)
    player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler

    settings = {
        Settings.PIPE: False,
        Settings.PITCH: 105,
        Settings.PLAYER: Players.MPLAYER,
        Settings.SPEED: 0,    # Undoubtedly settable, also supported by some players
        Settings.VOICE: '',
        Settings.VOLUME: 0
    }
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type(self)._class_name = self.__class__.__name__
        if type(self)._logger is None:
            type(self)._logger = module_logger.getChild(type(self)._class_name)
        self.festivalProcess = None

    def init(self):
        self.festivalProcess = None
        self.update()

    @staticmethod
    def isSupportedOnPlatform():
        return SystemQueries.isLinux()

    @staticmethod
    def isInstalled():
        installed = False
        if FestivalTTSBackend.isSupportedOnPlatform():
            installed = True
        return installed

    def getMode(self):
        player = type(self).getSetting(Settings.PLAYER)

        if type(self).getSetting(Settings.PIPE):
            return SimpleTTSBackendBase.PIPE
        else:
            return SimpleTTSBackendBase.WAVOUT

    def runCommand(self, text_to_voice, dummy):

        wave_file, exists = self.get_path_to_voice_file(text_to_voice, use_cache=False)

        wave_pipe = None
        return self.generate_speech(text_to_voice, wave_file)

    def runCommandAndPipe(self, text_to_voice):

        wave_file, exists = self.get_path_to_voice_file(text_to_voice, use_cache=False)

        wave_pipe = None
        if self.generate_speech(text_to_voice, wave_file):
            wave_pipe = io.BytesIO(wave_file)

        return wave_pipe

    def generate_speech(self, text_to_voice: str, wave_file: str):
        # In addition to festival, see the text2wave command

        if not text_to_voice:
            return None
        text_to_voice = text_to_voice.strip()
        if len(text_to_voice) == 0:
            return None

        volume = type(self).getVolume()
        volume = 1 * (10 ** (volume / 20.0))  # convert from dB to percent/100

        voice = type(self).getVoice()
        voice = voice and '(voice_{0})'.format(voice) or ''

        speed = type(self).getSpeed()
        durationMultiplier = 1.8 - (((speed + 16) / 28.0) * 1.4)  #
        # Convert from (-16 to +12) value to (1.8 to 0.4)
        durMult = durationMultiplier and "(Parameter.set 'Duration_Stretch {0})".format(
            durationMultiplier) or ''

        pitch = type(self).getPitch()
        pitch = pitch != 105 and "(require 'prosody-param)(set-pitch {0})".format(
            pitch) or ''

        # Assumption is to only adjust speech settings in engine, not player

        player_volume = 0.0  # '{:.2f}'.format(0.0)  # Don't alter volume (db)
        player_speed =  100.0  # '{:.2f}'.format(100.0)  # Don't alter speed/tempo (percent)
        # Changing pitch without impacting tempo (speed) is
        player_pitch = 100.0  # '{:.2f}'.format(100.0)  # Percent
        # not easy. One suggestion is to use lib LADSPA

        self.setPlayer(type(self).getSetting(Settings.PLAYER))
        self.player_handler.setVolume(player_volume)  # In db -12 .. 12
        self.player_handler.setSpeed(player_speed)
        self.player_handler.setPitch(player_pitch)

        self.festivalProcess = subprocess.Popen(['festival', '--pipe'],
                                                stdin=subprocess.PIPE,
                                                universal_newlines=True)
        text_to_voice = text_to_voice.replace('"', '\\"').strip()
        out = '(audio_mode \'async){0}{1}{2}(utt.save.wave (utt.wave.rescale (SynthText ' \
              '' \
              '"{3}") {4:.2f} nil)"{5}")\n'.format(
                     voice, durMult, pitch, text_to_voice, volume, wave_file)
        self.festivalProcess.communicate(out)
        return True

    def stop(self):
        try:
            self.festivalProcess.terminate()
        except:
            return

    @classmethod
    def settingList(cls, setting, *args):
        if setting == Settings.LANGUAGE:
            return [], None

        elif setting == Settings.VOICE:
            p = subprocess.Popen(['festival', '-i'], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True)
            d = p.communicate('(voice.list)')
            voices = list(
                map(str.strip, d[0].rsplit('> (', 1)[-1].rsplit(')', 1)[0].split(' ')))
            if voices:
                return [(v, v) for v in voices]  # name, id

        elif setting == Settings.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(Settings.PLAYER)

            return players, default_player

        return None

    @staticmethod
    def available():
        try:
            subprocess.call(['festival', '--help'], stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except (OSError, IOError):
            return False
        return True
