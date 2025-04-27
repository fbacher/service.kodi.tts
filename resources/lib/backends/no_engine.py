# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

from pathlib import Path

import langcodes
from backends.audio.sound_capabilities import ServiceType
from backends.base import SimpleTTSBackend
from backends.no_engine_settings import NoEngineSettings
from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import ServiceID, Services
from backends.settings.settings_map import Status
from backends.transcoders.trans import TransCode
from cache.common_types import CacheEntryInfo
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.logger import *
from common.phrases import Phrase
from common.setting_constants import (AudioType, Backends, Converters, Genders,
                                      PlayerMode)
from common.settings import Settings
from windowNavigation.choice import Choice

MY_LOGGER = BasicLogger.get_logger(__name__)


class NoEngine(SimpleTTSBackend):
    """

    """
    ID: str = Backends.NO_ENGINE_ID
    engine_id = Backends.NO_ENGINE_ID
    service_id: str = Services.NO_ENGINE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceID(service_type, service_id)
    displayName = 'noEngine'
    OUTPUT_FILE_TYPE: str = '.wav'
    UTF_8: Final[str] = '1'
    voice_cache: VoiceCache = None

    voice_map: Dict[str, List[Tuple[str, str, Genders]]] = None
    _class_name: str = None
    _initialized: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz.voice_cache = VoiceCache(clz.service_key, reset_engine_each_call=False)
        if not clz._initialized:
            clz._initialized = True
            BaseServices.register(self)

    @classmethod
    def get_voice_cache(cls) -> VoiceCache:
        return cls.voice_cache

    def init(self):
        super().init()
        clz = type(self)
        self.update()

    def get_output_audio_type(self) -> AudioType:
        return AudioType.WAV

    @classmethod
    def get_backend_id(cls) -> str:
        return cls.service_id

    @classmethod
    def init_voices(cls):
        cls.initialized_static = True

    def addCommonArgs(self, args, phrase: Phrase | None = None):
        clz = type(self)

    def get_player_mode(self) -> PlayerMode:
        return PlayerMode.FILE

    def create_wave_phrase(self, phrase: Phrase) -> Tuple[Phrase, CacheEntryInfo]:
        """
        Copy the given phrase produced by an engine and create a wave file from
        the previously created audio for the phrase. The wave file is placed
        in Constants.PREDEFINED_CACHE and is shipped with the product.
        :param phrase:
        :return: Phrase, CacheEntryInfo for the generated wave phrase
        """
        clz = type(self)
        if clz.voice_cache is None:
            clz.voice_cache = VoiceCache(clz.service_key)
        MY_LOGGER.debug(f'phrase: {phrase} \n'
                        f'text: {phrase.text} \n'
                        f'cache_path: {phrase.cache_path} \n'
                        f'audio_type: {phrase.audio_type} \n'
                        f'lang: {phrase.language} \n'
                        f'gender: {phrase.gender} \n'
                        f'voice: {phrase.voice} \n'
                        f'lang_dir: {phrase.lang_dir} \n'
                        f'territory_dir: {phrase.territory_dir}')
        wave_phrase: Phrase = Phrase(text=phrase.text,
                                     check_expired=False)
        wave_phrase.language = phrase.language
        wave_phrase.lang_dir = phrase.lang_dir
        wave_phrase.update_cache_path(active_engine=self)
        cache_info = clz.voice_cache.get_path_to_voice_file(wave_phrase, use_cache=True)
        MY_LOGGER.debug(f'wave_phrase: {wave_phrase} \n'
                        f'text: {wave_phrase.text} \n'
                        f'cache_path: {wave_phrase.cache_path} \n'
                        f'audio_type: {wave_phrase.audio_type} \n'
                        f'lang: {wave_phrase.language} \n'
                        f'gender: {wave_phrase.gender} \n'
                        f'voice: {wave_phrase.voice} \n'
                        f'lang_dir: {wave_phrase.lang_dir} \n'
                        f'territory_dir: {wave_phrase.territory_dir}')
        MY_LOGGER.debug(f'no_engine cache_info: {cache_info}')
        if not cache_info.audio_exists:
            mp3_file: Path = phrase.get_cache_path()
            wave_file = cache_info.final_audio_path
            # trans_id: str = Settings.get_transcoder(self.engine_id)
            trans_id: str = Converters.LAME
            MY_LOGGER.debug(f'service_id: {clz.service_id} trans_id: {trans_id}')
            success = TransCode.transcode(trans_id=trans_id,
                                          input_path=mp3_file,
                                          output_path=wave_file,
                                          remove_input=False)
            if success:
                phrase.text_exists(check_expired=False, active_engine=self)
            MY_LOGGER.debug(f'success: {success} wave_file: {wave_file} mp3: {mp3_file}')
        return wave_phrase, cache_info

    def get_cached_voice_file(self, phrase: Phrase,
                              generate_voice: bool = True) -> bool:
        """
        Return cached file if present, otherwise, generate speech, place in cache
        and return cached speech.

        Very similar to runCommand, except that the cached files are expected
        to be sent to a slave player_key, or some other player_key that can play a sound
        file.
        :param phrase: Contains the text to be voiced as wll as the path that it
                       is or will be located.
        :param generate_voice: If true, then wait a bit to generate the speech
                               file.
        :return: True if the voice file was handed to a player_key, otherwise False
        """
        clz = type(self)
        MY_LOGGER.debug(f'phrase: {phrase.get_text()} {phrase.get_debug_info()} '
                        f'cache_path: {phrase.get_cache_path()} use_cache: '
                        f'{Settings.is_use_cache()}')
        result: CacheEntryInfo
        result = clz.get_voice_cache().get_path_to_voice_file(phrase,
                                                      use_cache=Settings.is_use_cache())
        MY_LOGGER.debug(f'result: {result}')
        if result.audio_exists:
            return True
        return False

    def runCommand(self, phrase: Phrase) -> Path | None:
        """
        Run command to generate speech and save voice to a file (mp3 or wave).
        A player_key will then be scheduled to play the file. Note that there is
        delay in starting speech generator, speech generation, starting player_key
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
        # Conversions to/from the engine's or player_key's scale are done using
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
        cache path to reflect the chosen language but ignore territory.
        :param phrase:
        :return:
        """

        # NO_ENGINE is only used when no engine has been or able to be configured.
        # The audio comes shipped with the product with the sole purpose of guiding
        # the user to configuring an engine and player_key. To reduce the size of
        # these WAVE files, only audio for the major language is used. Territory
        # is ignored.
        if Settings.is_use_cache():
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'lang: {phrase.language} \n'
                                   f'voice: {phrase.voice}\n'
                                   f'lang_dir: {phrase.lang_dir}\n')
            locale: str = phrase.language  # IETF format
            _, kodi_locale, _, ietf_lang = LanguageInfo.get_kodi_locale_info()
            # MY_LOGGER.debug(f'orig Phrase locale: {locale}')
            if locale is None:
                locale = kodi_locale
            ietf_lang: langcodes.Language = langcodes.get(locale)
            # MY_LOGGER.debug(f'locale: {locale}')
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_territory_dir('')
        return

    @staticmethod
    def check_availability() -> Status:
        return NoEngineSettings.check_availability()
