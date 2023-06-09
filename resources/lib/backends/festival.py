# -*- coding: utf-8 -*-
import io
import os
import subprocess

#  from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
import sys

from backends.audio.sound_capabilties import SoundCapabilities
from backends.base import SimpleTTSBackendBase
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services, ServiceType
from common.logger import *
from common.base_services import BaseServices
from common.setting_constants import Backends, Players
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.system_queries import SystemQueries
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class FestivalTTSBackend(SimpleTTSBackendBase, BaseServices):
    backend_id = Backends.FESTIVAL_ID
    service_ID: str = Services.FESTIVAL_ID
    displayName = 'Festival'
    canStreamWav = SystemQueries.commandIsAvailable('mpg123')
    speedConstraints: Constraints = Constraints(-16, 0, 12, True, False, 1.0, SettingsProperties.SPEED)
    pitchConstraints: Constraints = Constraints(50, 105, 500, True, False, 1.0, SettingsProperties.PITCH)
    volumeConstraints: Constraints = Constraints(-12, 0, 12, True, True, 1.0, SettingsProperties.VOLUME)
    #  player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler
    constraints: Dict[str, Constraints] = {}

    _supported_input_formats: List[str] = []
    _supported_output_formats: List[str] = [SoundCapabilities.WAVE]
    _provides_services: List[ServiceType] = [ServiceType.ENGINE, ServiceType.PLAYER]
    sound_capabilities = SoundCapabilities(service_ID, _provides_services,
                                            _supported_input_formats,
                                            _supported_output_formats)
    settings = {
        SettingsProperties.PIPE: False,
        SettingsProperties.PITCH: 105,
        SettingsProperties.PLAYER: Players.MPLAYER,
        SettingsProperties.SPEED: 0,    # Undoubtedly settable, also supported by some players
        SettingsProperties.VOICE: '',
        SettingsProperties.VOLUME: 0
    }
    supported_settings: Dict[str, str | int | bool] = settings
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)
            clz.register(self)
        self.festivalProcess = None
        clz.constraints[SettingsProperties.SPEED] = clz.speedConstraints
        clz.constraints[SettingsProperties.PITCH] = clz.pitchConstraints
        clz.constraints[SettingsProperties.VOLUME] = clz.volumeConstraints

    def init(self):
        super().init()
        self.festivalProcess = None
        self.update()

    @classmethod
    def get_backend_id(cls) -> str:
        return Backends.FESTIVAL_ID

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
        clz = type(self)
        default_player: str = clz.get_setting_default(SettingsProperties.PLAYER)
        player: str = clz.get_player_setting(default_player)
        if clz.getSetting(SettingsProperties.PIPE):
            return SimpleTTSBackendBase.PIPE
        else:
            return SimpleTTSBackendBase.FILEOUT

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
        clz = type(self)
        if not text_to_voice:
            return None
        text_to_voice = text_to_voice.strip()
        if len(text_to_voice) == 0:
            return None

        volume = clz.getVolume()
        volume = 1 * (10 ** (volume / 20.0))  # convert from dB to percent/100

        voice = clz.getVoice()
        voice = voice and '(voice_{0})'.format(voice) or ''

        speed = self.getSpeed()
        durationMultiplier = 1.8 - (((speed + 16) / 28.0) * 1.4)  #
        # Convert from (-16 to +12) value to (1.8 to 0.4)
        durMult = durationMultiplier and "(Parameter.set 'Duration_Stretch {0})".format(
            durationMultiplier) or ''

        pitch = self.getPitch()
        pitch = pitch != 105 and "(require 'prosody-param)(set-pitch {0})".format(
            pitch) or ''

        # Assumption is to only adjust speech settings in engine, not player

        player_volume = 0.0  # '{:.2f}'.format(0.0)  # Don't alter volume (db)
        player_speed =  100.0  # '{:.2f}'.format(100.0)  # Don't alter speed/tempo (percent)
        # Changing pitch without impacting tempo (speed) is
        player_pitch = 100.0  # '{:.2f}'.format(100.0)  # Percent
        # not easy. One suggestion is to use lib LADSPA

        self.setPlayer(clz.get_player_setting())

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
        except AbortException:
            reraise(*sys.exc_info())
        except:
            return

    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[str], str]:
        if setting == SettingsProperties.LANGUAGE:
            return [], None

        elif setting == SettingsProperties.VOICE:
            p = subprocess.Popen(['festival', '-i'], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True)
            d = p.communicate('(voice.list)')
            voices = list(
                map(str.strip, d[0].rsplit('> (', 1)[-1].rsplit(')', 1)[0].split(' ')))
            if voices:
                return [(v, v) for v in voices]  # name, id

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            player_ids: List[str] = cls.get_players(include_builtin=False)
            default_player_id = cls.get_setting_default(SettingsProperties.PLAYER)

            return player_ids, default_player_id

        return None

    @staticmethod
    def available():
        try:
            subprocess.call(['festival', '--help'], stdout=(open(os.path.devnull, 'w')),
                            stderr=subprocess.STDOUT, universal_newlines=True)
        except (OSError, IOError):
            return False
        return True

    @classmethod
    def negotiate_engine_config(cls, backend_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        # if using cache
        # return True, True, True

        return False, False, False
