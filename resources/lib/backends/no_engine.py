# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import ctypes.util
import os
import subprocess
import sys
import tempfile

import langcodes

from pathlib import Path

from backends.players.iplayer import IPlayer
from backends.settings.language_info import LanguageInfo
from backends.settings.settings_helper import SettingsHelper
from backends.settings.validators import NumericValidator
from backends.transcoders.trans import TransCode
from cache.voicecache import VoiceCache
from cache.common_types import CacheEntryInfo
from common import *

from backends.audio.builtin_audio_player import BuiltInAudioPlayer
# from backends.audio.player_handler import BasePlayerHandler, WavAudioPlayerHandler
from backends.audio.sound_capabilities import ServiceType
from backends.base import BaseEngineService, SimpleTTSBackend
from backends.settings.i_validators import AllowedValue, INumericValidator, IValidator
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from common import utils
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
from common.messages import Messages
from common.monitor import Monitor
from common.phrases import Phrase
from common.setting_constants import (AudioType, Backends, Genders, Mode, PlayerMode,
                                      Players)
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from langcodes import LanguageTagError
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class NoEngine(SimpleTTSBackend):
    """

    """
    ID: str = Backends.NO_ENGINE_ID
    engine_id = Backends.NO_ENGINE_ID
    service_ID: str = Services.NO_ENGINE_ID
    service_TYPE: str = ServiceType.ENGINE_SETTINGS
    displayName = 'noEngine'
    OUTPUT_FILE_TYPE: str = '.wav'
    UTF_8: Final[str] = '1'

    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        self.voice_cache: VoiceCache = VoiceCache(clz.service_ID)
        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    def init(self):
        super().init()
        clz = type(self)
        self.update()

    def get_output_audio_type(self) -> AudioType:
        return AudioType.WAV

    def get_voice_cache(self) -> VoiceCache:
        return self.voice_cache

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.service_ID

    @classmethod
    def init_voices(cls):
        cls.initialized_static = True

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)

    def get_player_mode(self) -> PlayerMode:
        return PlayerMode.FILE

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Return cached file if present, otherwise, generate speech, place in cache
        and return cached speech.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player, or some other player that can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player, otherwise False
        """
        MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                        f'cache_path: {phrase.get_cache_path()} use_cache: '
                        f'{Settings.is_use_cache()}')
        result: CacheEntryInfo
        result = self.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache())
        MY_LOGGER.debug(f'result: {result}')
        if result.audio_exists:
            return True
        return False

    def runCommand(self, phrase: Phrase) -> Path | None:
        """
        Run command to generate speech and save voice to a file (mp3 or wave).
        A player will then be scheduled to play the file. Note that there is
        delay in starting speech generator, speech generation, starting player
        up and playing. Consider using caching of speech files as well as
        using PlayerMode.SLAVE_FILE.
        :param phrase:
        :return: If Successful, path of the wave file (may not have a suffix!)
                 Otherwise, None
       """
        if self.get_cached_voice_file(phrase, generate_voice=False):
            return phrase.get_cache_path()

    def stop(self):
        clz = type(self)
        return

    @classmethod
    def load_languages(cls):
        """
        Discover eSpeak's supported languages and report results to
        LanguageInfo.
        :return:
        """
        return

    @classmethod
    def settingList(cls, setting, *args) -> Tuple[List[Choice], str]:
        return [], ''

    @classmethod
    def get_default_language(cls) -> str:
        return ''

    @classmethod
    def get_voice_id_for_name(cls, name):
        return ''

    def getVolume(self) -> int:
        return 0

    def get_pitch(self) -> int:
        # All pitches in settings use a common TTS scale.
        # Conversions to/from the engine's or player's scale are done using
        # Constraints
        return 0

    def get_speed(self) -> int:
        """
            espeak's speed is measured in 'words/minute' with a default
            of 175. Limits not specified, appears to be about min=60 with no
            max. Linear

            By contrast, mplayer linearly adjusts the 'speed' of play with
            0.25 playing at 1/4th speed (or 4x the time)
        :return:
        """
        return 1

    @classmethod
    def update_voice_path(cls, phrase: Phrase) -> None:
        """
        If a language is specified for this phrase, then modify any
        cache path to reflect the chosen language and territory.
        :param phrase:
        :return:
        """

        if Settings.is_use_cache() and not phrase.is_lang_territory_set():
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'lang: {phrase.language} \n'
                                   f'voice: {phrase.voice}\n'
                                   f'lang_dir: {phrase.lang_dir}\n'
                                   f'')
            locale: str = phrase.language  # IETF format
            _, kodi_locale, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            # MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            ietf_lang: langcodes.Language = langcodes.get(locale)
            # MY_LOGGER.debug(f'locale: {locale}')
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_territory_dir(ietf_lang.territory.lower())
        return

    @staticmethod
    def available() -> bool:
        return True
