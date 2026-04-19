# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from pathlib import Path

import gtts
import langcodes
from backends import base
from backends.engines.google_downloader import MyGTTS
from backends.engines.speech_generator import SpeechGenerator
from backends.engines.utils.igenerator_deps import ITTSData
from backends.google_data import GoogleData
from backends.ispeech_generator import ISpeechGenerator
from backends.players.iplayer import IPlayer
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import (EngineType, QualityType, ServiceID,
                                             ServiceKey, Services,
                                             ServiceType)
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_helper import SettingsHelper
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.debug import Debug
from common.logger import *
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import AudioType, Backends, Genders, PlayerMode
from common.settings import Settings
from gtts import gTTS, lang
from langcodes import LanguageTagError
from windowNavigation.choice import Choices, VGChoices

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class LangInfo:
    """
    Manages the language choices for gTTS.
    """

    lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
    initialized: bool = False
    global_lang_initalized: bool = False

    @classmethod
    def load_voices(cls):
        """
        Get all supported languages from GTTS. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.... Finally,
        hand off the entries to Kodi TTS.

        :return:
        """
        if cls.initialized:
            return

        cls.initialized = True
        MY_LOGGER.debug(f'In load_voices')
        lang_map: Dict[str, str] = gtts.lang.tts_langs()
        engine_quality: int = EngineType.GOOGLE.ordinal
        voice_quality: QualityType = QualityType.HIGH  # High quality

        """
          Only the keys are of interest. The key is usually a simple
          language code, but can be lang-territory.
          The value is simple an English translation of the key. 
          langcodes gives us the translation for many languages.

        The dictionary returned combines languages from two origins:
          - Languages fetched from Google Translate (pre-generated in gtts.langs)
          - Languages that are undocumented variations that were observed to work 
            and present different dialects or accents.
        """
        # Convert to langcodes
        # User can only choose a voice that belongs to the current major
        # language
        current_language: str = langcodes.Language.get(Constants.LOCALE).language

        ietf_langs: List[langcodes.Language] = []
        for gtts_lang in lang_map.keys():
            #  MY_LOGGER.debug(f'gtts_lang: {gtts_lang}')
            gtts_lang: str
            ietf_lang: langcodes.Language
            try:
                ietf_lang = langcodes.Language.get(gtts_lang)
                # Ignore language that does not match what Kodi is set to
                if ietf_lang.language != current_language:
                    continue
                ietf_langs.append(ietf_lang)
                #  MY_LOGGER.debug(f'ietf_langs added {ietf_lang}')
            except AbortException as e:
                reraise(*sys.exc_info())
            except LanguageTagError:
                MY_LOGGER.exception('')

        """
        Get an informal list of language variants for each
        language. For example, 'en' (english) is spoken in (at least)
        the following territories:
          ['ag', 'au', 'bw', 'ca', 'dk', 'gb', 'hk', 'ie', 'il', 'in', 
           'ng', 'nz', 'ph', 'sc', 'sg', 'us', 'za', 'zm', 'zw']
        """
        extra_locales: Dict[str, str] = GoogleData.get_locales()
        # Again, we only care about the key, which is a lang-territory code.
        # The value is an English description

        ietf_lang_territories: List[langcodes.Language] = []
        for gtts_lang_territory in extra_locales.keys():
            #  MY_LOGGER.debug(f'gtts_lang_territory: {gtts_lang_territory}')
            gtts_lang_territory: str
            ietf_lang_terr: langcodes.Language
            try:
                ietf_lang_terr = langcodes.Language.get(gtts_lang_territory)
                if ietf_lang_terr.language != current_language:
                    continue
                ietf_lang_territories.append(ietf_lang_terr)
                # pt-BR
                # MY_LOGGER.debug(f'adding {ietf_lang_terr} to ietf_lang_territories')
            except AbortException as e:
                reraise(*sys.exc_info())
            except LanguageTagError:
                MY_LOGGER.exception('')

        """
        Now for getting this all together. 
          - Use the ietf_langs as the authoritative list of languages
            supported by GTTS.
          - Create langcode instances for each ietf_lang, extra_locale.
          - Create combined langcode list from the two above where 
          - the language is in common but the territory is not.
          - Finally, create Voice instances
        """

        # Use a map[<locale_id>, Dict[<langcode>, None]] for the combined
        # set of language variants for each locale_id. Second Dict
        # has None value because it is being used as a set.
        lang_variants: Dict[str, Dict[str, None]] | None = {}
        # Make sure the primary language has an entry ('en')
        ietf_lang: langcodes.Language
        for ietf_lang in ietf_lang_territories:
            #  MY_LOGGER.debug(f'ietf_lang: {ietf_lang}')
            lang_code: str = ietf_lang.language
            variants: Dict[str, None] = lang_variants.get(lang_code)
            if variants is None:
                variants = {}
                lang_variants[lang_code] = None

        # Now, that primary lang added, add the variants (en-us, en-gb...)

        #  ietf_langs: List[langcodes.Language]
        ietf_lang_territories: List[langcodes.Language]
        lang_variants: Dict[str, Dict[str, None]]
        ietf_lang: langcodes.Language
        for ietf_lang in ietf_lang_territories:
            locale_id: str = ietf_lang.to_tag()  # Mixed case
            engine_lang_id: str = locale_id
            MY_LOGGER.debug(f'Adding language')
            EngineVoiceManager.add_language(engine_key=GoogleTTSEngine.service_key,
                                            ietf_tag=locale_id,
                                            engine_lang_id=engine_lang_id)
            MY_LOGGER.debug(f'added language')
            voice_name: str = locale_id
            try:
                voice_name = langcodes.Language.get(locale_id).display_name()
            except AbortException as e:
                reraise(*sys.exc_info())
            except:
                pass

            locale_id: str = locale_id.lower()
            # Will create (dummy) Voice Groups for each voice
            cache_path_segment: Path = Path(ietf_lang.to_tag().lower())
            label: str = f'{locale_id} {voice_name}'
            voice_label: str = (f'{voice_name}  Quality: {QualityType} '
                                f' Voice Locale: {locale_id}')

            EngineVoiceManager.add_voice(engine_key=GoogleTTSEngine.service_key,
                                         ietf_tag=ietf_lang.to_tag(),
                                         gender=Genders.ANY,
                                         engine_lang_id=locale_id,
                                         e_voice_id=locale_id,
                                         engine_vg_id=locale_id,
                                         voice_quality=voice_quality,
                                         voice_label=voice_label,
                                         cache_path_segment=cache_path_segment)


class GoogleTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.GOOGLE_ID
    engine_id: ServiceID = Backends.GOOGLE_ID
    service_id: str = Services.GOOGLE_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceKey.GOOGLE_KEY
    MAX_PHRASE_KEY: ServiceID = service_key.with_prop(SettingProp.MAX_PHRASE_LENGTH)
    displayName = 'GoogleTTS'
    maximum_wait_sec: float = 10.0

    _logger: BasicLogger = None
    # lang_map: Dict[str, str] = None # IETF_lang_name: display_name
    _initialized: bool = False

    @classmethod
    def load_voices(cls) -> None:
        """
        Determines the voices supported by GoogleTTS and converts them
        into a format that Kodi TTS likes

        :return:
        """
        LangInfo.load_voices()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)

        self.f = False
        self.voice_cache: VoiceCache = VoiceCache(service_key=GoogleTTSEngine.service_key)
        clz.load_voices()
        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True

    def init(self) -> None:
        clz = type(self)
        super().init()
        self.update()

    def get_voice_cache(self) -> VoiceCache:
        return self.voice_cache

    def get_player_mode(self) -> PlayerMode:
        clz = type(self)
        player: IPlayer = self.get_player(self.service_key)
        player_mode: PlayerMode = Settings.get_player_mode(clz.service_key)
        return player_mode

    @classmethod
    def update_voice_path(cls, phrase: Phrase) -> None:
        """
        If a language is specified for this phrase, then modify any
        cache path to reflect the chosen language and territory.
        :param phrase:
        :return:
        """
        MY_LOGGER.debug(f'update_voice_path phrase: {phrase}')
        locale_id: str = phrase.language  # IETF format
        if phrase.language is None:
            locale_id = LangUtils.kodi_locale
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'orig Phrase locale_id: {locale_id}')
        ietf_lang: langcodes.Language = langcodes.get(locale_id)
        e_voice: EngineVoice = EngineVoiceManager.get_e_voice(cls.service_key)

        if Settings.is_use_cache() and not phrase.is_lang_territory_set():
            phrase.set_lang_dir(ietf_lang.language)
            phrase.set_territory_dir(ietf_lang.territory.lower())
            MY_LOGGER.debug(f'language/territory being set text: {phrase.text} '
                            f'lang: {ietf_lang}')
            phrase.set_e_voice(e_voice)
            phrase.set_voice_dir(e_voice.cache_path_segment)
        else:
            phrase.set_e_voice(e_voice)
            phrase.set_voice_dir(e_voice.cache_path_segment)
        return

    def create_speech_generator(self,
                                tts_data: ITTSData | None = None) -> ISpeechGenerator | None:
        """
        Provides a means to pass generator-specific data

        :param tts_data: Optional data
        """
        generator: SpeechGenerator
        generator = SpeechGenerator(engine_instance=self,
                                    downloader=MyGTTS(),
                                    max_phrase_length=self.generation_chunk_size)
        return generator

    def runCommand(self, phrase: Phrase) -> bool:
        clz = type(self)
        # Caching is ALWAYS used here, otherwise the delay would be maddening.
        # Therefore, this is primarily called when the voice file is NOT in the
        # cache. In this case it is also ONLY called by the background thread
        # in SeedCache.
        # It can also be called by the TTS engine during configuration. In this case
        # it is okay if it is a little slow.
        #
        generator: ISpeechGenerator
        generator = self.create_speech_generator()
        cache_file_state: CacheFileState
        cache_file_state = generator.get_voiced_file(phrase,
                                                     player_mode=PlayerMode.SLAVE_FILE)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        return cache_file_state == CacheFileState.OK

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def generation_chunk_size(self) -> int:
        """
        :return: the maximum character length of the audio generator. Use a very
                large number, such as a million, for unlimited length
        """
        return gTTS.GOOGLE_TTS_MAX_CHARS

    @property
    def supports_caching(self) -> bool:
        return Settings.is_use_cache()

    def runCommandAndPipe(self, phrase: Phrase) -> BinaryIO | None:
        """
        TODO: Change to pass a byte-stream back (or into) get_voiced_file/generate.
              Do in such a way that the pipe is opened asap to avoid rereading
              cache.
        :param phrase:
        :return:
        """
        generator: ISpeechGenerator
        generator = self.create_speech_generator()
        cache_file_state: CacheFileState
        cache_file_state = generator.get_voiced_file(phrase,
                                                     player_mode=PlayerMode.SLAVE_FILE)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        if cache_file_state != CacheFileState.OK:
            return None
        MY_LOGGER.debug(f'Creating {phrase.get_cache_path()}')
        byte_stream: BinaryIO | None = None
        byte_stream = phrase.get_cache_path().open(mode='br')
        return byte_stream

        '''
        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file
        '''

    def seed_text_cache(self, phrases: PhraseList) -> None:
        """
        Provides means to generate voice files before actually needed. Currently
        called by worker_thread to get a bit of a head-start on the normal path.
        (Probably does not help much). Also, called by disabled code which
        :param phrases:
        :return:
        """
        self.get_voice_cache().seed_text_cache(phrases)

    def update(self):
        pass

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def _stop(self):
        """
        Stop producing current audio. Originates from KodiPlayerMonitor
        :return:
        """
        clz = type(self)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v('stop')

    @classmethod
    def has_speech_generator(cls) -> bool:
        return True

    @classmethod
    def settingList(cls, setting: str,
                    *args) -> Tuple[Choices, str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translate). Sorting/translating done
        in UI.

        :param setting: name of the setting
        :param args: Not used
        :return:
        """
        if setting == SettingProp.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale_id

            cls.load_languages()
            MY_LOGGER.debug(f'Who uses this?')
            Debug.dump_current_thread()

            vg_choices: VGChoices
            vg_choices = SettingsHelper.get_vg_choices(cls.service_key)
            best_vg: int = vg_choices.default_vg_idx
            default_setting: str = vg_choices[best_vg].lang_info.locale_id.lower()
            return vg_choices, default_setting

        elif setting == SettingProp.PLAYER:
            # Get list of player ids. Id is same as is stored in settings.xml

            default_player: str = cls.get_setting_default(SettingProp.PLAYER)
            player_ids: Choices = Choices()
            return player_ids, default_player
        return Choices(), 'No Player'

    @classmethod
    def get_voice(cls) -> EngineVoice:
        e_voice: EngineVoice = EngineVoiceManager.get_e_voice(cls.service_key)
        return e_voice

    @classmethod
    def getLanguage(cls) -> str:
        """
        Gets the current locale_id ex: en-us

        :return:
        """
        language: str = Settings.get_language(cls.service_key)
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingProp.LANGUAGE)
        language = default_lang
        # language_validator: StringValidator
        # language_validator = cls.get_validator(cls.setting_id,
        #                                        setting_id=SettingProp.LANGUAGE)
        # language = language_validator.get_tts_value()
        return language

    @classmethod
    def getPitch(cls) -> float:
        """
        Pitch is not settable on Google TTS

        :return:
        """

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender

    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingProp.API_KEY)
