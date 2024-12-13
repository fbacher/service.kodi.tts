# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import os
import subprocess

from common import *

#  from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.base import SimpleTTSBackend
from backends.settings.constraints import Constraints
from backends.settings.service_types import Services
from common.constants import Constants
from common.logger import *
from common.setting_constants import Backends
from common.settings import Settings
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_logger(__name__)


class Pico2WaveTTSBackend(SimpleTTSBackend):
    ID = Backends.ESPEAK_ID
    service_ID: str = Services.PICO_TO_WAVE_ID
    initialized: bool = False
    engine_id = Backends.PICO_TO_WAVE_ID
    _engine_id = Backends.PICO_TO_WAVE_ID
    displayName = 'pico2wave'
    speedConstraints: Constraints = Constraints(20, 100, 200, True, False, 1.0,
                                                SettingsProperties.SPEED)
    #  player_handler_class: Type[BasePlayerHandler] = WavAudioPlayerHandler
    constraints: Dict[str, Constraints] = {}
    settings = {SettingsProperties.LANGUAGE: '',
                SettingsProperties.PLAYER  : None,
                SettingsProperties.SPEED   : 0,
                SettingsProperties.VOLUME  : 0
                }
    supported_settings: Dict[str, str | int | bool] = settings
    _logger: BasicLogger = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger
        if not clz._initialized:
            clz._initialized = True
            self.register(self)
        self.language = None
        self.stop_processing = False
        self.initialized = False  # For reinitialization, super classes use
        clz.constraints[SettingsProperties.SPEED] = clz.speedConstraints

    def init(self):
        super().init()
        self.festivalProcess = None
        self.update()

    @classmethod
    def get_backend_id(cls) -> str:
        return Backends.FESTIVAL_ID

    def runCommand(self, text_to_voice, dummy):
        clz = type(self)
        self.process = None
        self.stop_processing = False

        # If caching is enabled, voice_file will be in the cache.

        voice_file, exists = self.get_path_to_voice_file(text_to_voice,
                                                         use_cache=Settings.is_use_cache())
        self._logger.debug_v('pico2wave.runCommand text: ' + text_to_voice +
                                   ' language: ' + self.language)
        args = ['pico2wave']
        if self.language:
            args.extend(['-l', clz.getLanguage()])
        args.extend(['-w', '{0}'.format(voice_file), '{0}'.format(text_to_voice)])
        try:
            if not self.stop_processing:
                with subprocess.call(args, universal_newlines=True) as self.process:
                    pass
                self.process = None
        except Exception as e:
            self.process = None
            self._logger.error('Failed to download voice file: {}'.format(str(e)))
            try:
                os.remove(voice_file)
            except Exception as e2:
                pass
            return False

        if self.stop_processing:
            self._logger.debug_v('runCommand stop_processing')
            return False

        return True

    def update(self):
        pass

    @classmethod
    def settingList(cls, setting, *args):
        if setting == 'language':
            try:
                out = subprocess.check_output(
                        ['pico2wave', '-l', 'NONE', '-w', '/dev/null', 'X'],
                        stderr=subprocess.STDOUT,
                        universal_newlines=True)
            except subprocess.CalledProcessError as e:
                out = e.output
            if 'languages:' not in out:
                return None

            languages = [(v, v) for v in
                         out.split('languages:', 1)[-1].split('\n\n')[0].strip(
                                 '\n').split('\n')]

            default_locale = Constants.LOCALE.lower().replace('_', '-')
            default_language = languages[0][0]
            for language, language_id in languages:
                if default_locale == language_id:
                    default_language = default_locale

            return languages, default_language

        elif setting == SettingsProperties.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            players = cls.get_players(include_builtin=False)
            default_player = cls.get_setting_default(SettingsProperties.PLAYER)

            return players, default_player

        return None

    @classmethod
    def negotiate_engine_config(cls, engine_id: str, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing engine to control
        """
        # if using cache
        # return True, True, True

        return True, True, True
