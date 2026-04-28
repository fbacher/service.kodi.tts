# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from pathlib import Path

import langcodes
from backends import base
from backends.engines.idownloader import OutputType
from backends.engines.piper_api import (PiperApi, PiperData,
                                        PiperDownloader,
                                        PiperSpeakerTuple)
from backends.engines.speech_generator import SpeechGenerator
from backends.ispeech_generator import ISpeechGenerator
from backends.players.iplayer import IPlayer
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import (EngineType, QualityType, ServiceID,
                                             ServiceKey, Services,
                                             ServiceType)
from backends.settings.setting_properties import SettingProp
from cache.common_types import CacheEntryInfo
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.debug import Debug
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList
from common.setting_constants import Backends, Genders, PlayerMode
from common.settings import Settings
from langcodes import LanguageTagError
from windowNavigation.choice import Choice, Choices

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class LangInfo:
    """
    Manages the language choices for piper.
    """

    lang_info_map: Dict[str, ForwardRef('LangInfo')] = {}
    initialized: bool = False
    voices_initialized_initialized: bool = False
    global_lang_initalized: bool = False
    lang_limit: int = 0
    MAX_LANG_LIMIT: int = 5

    @classmethod
    def load_voices(cls):
        """
        Get all supported languages from piper. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.... Finally,
        hand off the entries to Kodi TTS.

        :return:
        """
        MY_LOGGER.debug(f'load_voices')
        if not cls.initialized:
            cls.initialized = True
            # User can only choose a voice that belongs to the current major
            # language
            current_language: str = langcodes.Language.get(Constants.LOCALE).language
            engine_quality: int = EngineType.PIPER.ordinal

            cls.start_http_server()

            speakers: List[PiperSpeakerTuple] | None
            speakers = PiperApi.tts_langs(current_language)
            """
            Each entry can represent either a single voice, or it can represent
            a voice with multiple speakers.
            
            When the entry is for a single voice, then a vg_id of '0'
            is returned. Otherwise, None is returned. 
            
            Entries with non-0 id speakers are added immediately after an entry with
            a vg_id of None.
            
            """
            # Convert to langcodes
            ietf_langs: List[langcodes.Language] = []
            for piper_lang in speakers:
                MY_LOGGER.debug(f'piper_lang: {piper_lang}')
                piper_lang: PiperSpeakerTuple = piper_lang
                lang_territory_code: str = piper_lang.lang_territory_code
                # The voice_group always refers to the filename prefix describing the
                # voice or voice group.
                #
                # The vg_label refers to either the name of the single voice
                # of the voice group, or one of the speakers in the group.
                #
                # The vg_id refers to the index of a defined voice, or
                # zero when there are no defined speakers, or '', when
                # the entry is for the group description preceding the voice
                # entries.

                speaker_id: str = piper_lang.speaker_id
                speaker_name: str = piper_lang.speaker_name

                # TEST
                # if speaker_name != 'semaine':
                #     continue

                voice_group_id: str = piper_lang.voice_id
                voice_quality: int = piper_lang.quality.ordinal
                ietf_lang: langcodes.Language
                try:
                    ietf_lang = langcodes.Language.get(lang_territory_code)
                    if ietf_lang.language != current_language:
                        continue

                    ietf_langs.append(ietf_lang)
                    voice_id: str = f'{voice_group_id}-{speaker_id}'
                    voice_name: str = speaker_name

                    MY_LOGGER.debug(f'speaker_name: {speaker_name}\n'
                                    f'voice_name: {voice_name}\n'
                                    f'vg_id: {voice_id}')
                    EngineVoiceManager.add_language(engine_key=PiperTTSEngine.service_key,
                                                    ietf_tag=ietf_lang.to_tag(),
                                                    engine_lang_id=ietf_lang.to_tag())
                except AbortException:
                    reraise(*sys.exc_info())
                except LanguageTagError:
                    MY_LOGGER.exception('')

            cls.load_speakers(speakers)

    @classmethod
    def start_http_server(cls):
        pass


    @classmethod
    def load_speakers(cls, speakers_data: List[PiperSpeakerTuple]):
        """
        Get all supported languages from piper. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.... Finally,
        hand off the entries to Kodi TTS.

        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'In load_speakers')
        if not cls.voices_initialized_initialized:
            cls.voices_initialized_initialized = True

            # User can only choose a voice that belongs to the current major
            # language
            current_language: str = langcodes.Language.get(Constants.LOCALE).language

            """
            Each entry can represent either a voice with one speaker, or it can represent
            a voice with multiple speakers.

            When the entry is for a voice of one voice, then a vg_id of '0'
            is returned. Otherwise, None is returned. 

            Entries the different speakers are added immediately after an entry with
            a vg_id of None.

            """
            # Convert to langcodes
            ietf_langs: List[langcodes.Language] = []
            for speaker_data in speakers_data:
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'speaker_data: {speaker_data}')
                speaker_data: PiperSpeakerTuple
                lang_territory_code: str = speaker_data.lang_territory_code
                # The voice_group always refers to the filename prefix describing the
                # voice or voice group.
                #
                # The vg_label refers to either the name of the single voice
                # of the voice group, or one of the speakers in the group.
                #
                # The vg_id refers to the index of a defined voice, or
                # zero when there are no defined speakers, or '', when
                # the entry is for the group description preceding the voice
                # entries.
                vg_name: str = speaker_data.vg_name
                speaker_id: str = speaker_data.speaker_id
                speaker_name: str = speaker_data.speaker_name
                # TEST
                # if speaker_name != 'semaine':
                #     continue

                vg_id: str = speaker_data.voice_id
                voice_quality: QualityType = speaker_data.quality
                ietf_lang: langcodes.Language
                try:
                    ietf_lang = langcodes.Language.get(lang_territory_code)
                    if ietf_lang.language != current_language:
                        continue
                    ietf_langs.append(ietf_lang)
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'ietf_langs added {ietf_lang}')
                    voice_name: str = speaker_name
                    locale_id: str = ietf_lang.to_tag()  # Mixed case
                    lower_locale_id: str = locale_id.lower()
                    if False:
                        MY_LOGGER.debug(f'engine_key: {PiperTTSEngine.service_key}\n'
                                        f'ietf_tag: {locale_id}\n'
                                        f'gender: {Genders.ANY}\n'
                                        f'default_voice_id: {speaker_id}\n'
                                        f'engine_lang_id: {lower_locale_id}\n'
                                        f'engine_vg_id: {vg_id}\n'
                                        f'voice_quality: {voice_quality.label}\n'
                                        f'vg_label: {vg_name}\n'
                                        f'speaker_name: {speaker_name}\n'
                                        f'voice_name: {voice_name}\n'
                                        f'voice_id: {speaker_id}'
                                        f'vg_id: {vg_id}')
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'speaker_id: {speaker_id} type: '
                                          f'{type(speaker_id)}')
                    if speaker_id == '0':
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'VOICE GROUP\n'
                                        f'engine_key: {PiperTTSEngine.service_key}\n'
                                        f'ietf_tag: {locale_id}\n'
                                        f'gender: {Genders.ANY}\n'
                                        f'default_voice_id: {speaker_id}\n'
                                        f'engine_lang_id: {lower_locale_id}\n'
                                        f'engine_vg_id: {vg_id}\n'
                                        f'voice_quality: {voice_quality.label}\n'
                                        f'vg_name: {vg_name}')
                            MY_LOGGER.debug_v(f'vg_name: {vg_name}')
                        current_vg = EngineVoiceManager.add_voice_group(
                                engine_key=PiperTTSEngine.service_key,
                                ietf_tag=locale_id,
                                gender=Genders.ANY,
                                default_voice_id=speaker_id,
                                engine_lang_id=locale_id,
                                engine_vg_id=vg_id,
                                voice_quality=voice_quality,
                                vg_label=vg_name)
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'VOICE\n'
                                    f'engine_key: {PiperTTSEngine.service_key}\n'
                                    f'ietf_tag: {locale_id}\n'
                                    f'gender: {Genders.ANY}\n'
                                    f'engine_lang_id: {lower_locale_id}\n'
                                    f'e_voice_id: {speaker_id}\n'
                                    f'engine_vg_id: {vg_id}\n'
                                    f'voice_quality: {voice_quality.label}\n'
                                    f'voice_label: {voice_name}')

                    current_voice = EngineVoiceManager.add_voice(
                            engine_key=PiperTTSEngine.service_key,
                            ietf_tag=locale_id,
                            gender=Genders.ANY,
                            engine_lang_id=lower_locale_id,
                            e_voice_id=speaker_id,
                            engine_vg_id=vg_id,
                            voice_quality=voice_quality,
                            voice_label=voice_name)
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'VOICE\n new_voice: {current_voice}')
                except AbortException as e:
                    reraise(*sys.exc_info())
                except LanguageTagError:
                    MY_LOGGER.exception('')


class PiperTTSEngine(base.SimpleTTSBackend):
    ID: str = Backends.PIPER_ID
    engine_id: str = Backends.PIPER_ID
    service_id: str = Services.PIPER_ID
    service_type: ServiceType = ServiceType.ENGINE
    service_key: ServiceID = ServiceKey.PIPER_KEY
    MAX_PHRASE_KEY: ServiceID = service_key.with_prop(SettingProp.MAX_PHRASE_LENGTH)
    MAX_CHUNK_SIZE: int = 4096
    displayName = 'Piper TTS'

    _logger: BasicLogger = None
    _initialized: bool = False

    @classmethod
    def load_voices(cls) -> None:
        """
          Determines the languages supported by Piper and converts them
          into a format that Kodi TTS likes

          :return:
          """
        LangInfo.load_voices()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)

        MY_LOGGER.debug(f'In piper.init')

        PiperApi.start_builtin_http_server()

        self.f = False
        self.voice_cache: VoiceCache = VoiceCache(service_key=PiperTTSEngine.service_key)
        clz.load_voices()

        if not clz._initialized:
            BaseServices().register(self)
            clz._initialized = True

        #  TESTING
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            voice_name: str = 'p3922'
            voice_id: str = 'en_US-libritts-high-0'
            uid: str = ServiceID.get_uid(clz.service_key, voice_id)
            MY_LOGGER.debug(f'uid: {uid}')
            voice: EngineVoice
            voice = EngineVoiceManager.get_eng_voice_by_uid(uid)
            if voice is None or voice.e_voice_id != voice_id:
                MY_LOGGER.debug(f'FAILED Unable to find Voice {voice_id} {voice}')
                vgs_by_engine: Dict[str, EngineVoiceGroup]
                vgs_by_engine = EngineVoiceManager.engine_vg_by_engine_id[clz.service_key]
                for vg_id, vg in vgs_by_engine.items():
                    vg_id: str
                    vg: EngineVoiceGroup
                    MY_LOGGER.debug(f'vg_id: {vg_id} vg: {vg.engine_vg_id}')
                    for v_id, v in vg.e_voices.items():
                        v_id: str
                        v: EngineVoice
                        MY_LOGGER.debug(f'      v: v_id: {v_id} voice: {v}')

                # return
            vg_id: str = 'en_US-libritts-high'
            uid = ServiceID.get_uid(clz.service_key, vg_id)
            vg: EngineVoiceGroup
            vg = EngineVoiceManager.vg_by_uid.get(uid)
            if vg is None:
                MY_LOGGER.debug(f"Can't find VoiceGroup with uid: "
                                f"{uid}")
            vg = EngineVoiceManager.get_vg(vg_id, clz.service_key)
            if vg is None:
                MY_LOGGER.debug(f'Can\'t find VoiceGroups for vg_id {vg_id} and '
                                f'service_key: {clz.service_key}')
            else:
                voice: EngineVoice = vg.e_voices.get(vg.default_voice_id)
                if voice is None:
                    MY_LOGGER.debug('FAILED to get voice 0')
                    MY_LOGGER.debug(f'vg.voices: {vg.e_voices.keys()}')
                if voice.voice_label != voice_name:
                    MY_LOGGER.debug(f'FAILED. Voice label not {voice_name}')
            engine_vgs: Dict[str, EngineVoiceGroup]
            engine_vgs = EngineVoiceManager.engine_vg_by_engine_id.get(clz.service_key)
            if engine_vgs is None:
                MY_LOGGER.debug(f'FAILED TO find engine_vgs for Piper')
                return
            vg = engine_vgs.get(voice.engine_vg_id)
            if vg is None:
                MY_LOGGER.debug(f'FAILED to find vg with vg_id {voice.engine_vg_id}')
                return
            default_voice_id: str = vg.default_voice_id
            if default_voice_id is None:
                MY_LOGGER.debug(f'FAILED to find default_voice_id for Piper')
                return
            MY_LOGGER.debug(f'default_voice_id: {default_voice_id}')
            if default_voice_id != voice_id:
                MY_LOGGER.debug(f'FAILED. Default_voice_id != {voice_id}')
                return

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
    def supports_voice_groups(cls) -> bool:
        return True

    def create_speech_generator(self,
                                tts_data: PiperData | None = None) \
            -> ISpeechGenerator | None:
        """
        Provides a means to pass generator-specific data

        :param tts_data: Optional data
        """
        kwargs: Dict[str, Any] = {'use_fp_for_tmp': False}
        max_chunk_size: int = PiperApi.PIPER_TTS_MAX_CHARS

        piper_downloader: PiperDownloader
        piper_downloader = PiperDownloader(output_type=OutputType.USE_FILE,
                                           tts_data=tts_data)
        generator: SpeechGenerator
        generator = SpeechGenerator(engine_instance=self,
                                    downloader=piper_downloader,
                                    max_phrase_length=max_chunk_size,
                                    **kwargs)
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
                                                     player_mode=PlayerMode.PIPE)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        return cache_file_state == CacheFileState.OK

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
                                                     player_mode=PlayerMode.PIPE)
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase}')
        if cache_file_state != CacheFileState.OK:
            return None
        byte_stream: BinaryIO | None = None
        byte_stream = phrase.get_cache_path().open(mode='br')
        return byte_stream

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
                    *args) -> Tuple[List[Choice], str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translate). Sorting/translating done
        in UI.

        :param setting: name of the setting
        :param args: Not used
        :return:
        """
        raise NotImplementedError()

    @classmethod
    def get_voice(cls) -> EngineVoice:
        e_voice: EngineVoice = EngineVoiceManager.get_e_voice(cls.service_key)
        return e_voice

    '''
    @classmethod
    def getLanguage(cls) -> str:
        """
        Gets the current locale_id ex: en-us

        :return:
        """
        MY_LOGGER.debug(f'In getLanguage')
        language: str = Settings.get_language(cls.service_key)
        languages: List[Tuple[str, str]]  # lang_id, locale_id
        languages, default_lang = cls.settingList(SettingProp.LANGUAGE)
        language = default_lang
        # language_validator: StringValidator
        # language_validator = cls.get_validator(cls.setting_id,
        #                                        setting_id=SettingProp.LANGUAGE)
        # language = language_validator.get_tts_value()
        return language
    '''

    @classmethod
    def getPitch(cls) -> float:
        """
        Pitch is not settable on Piper TTS

        :return:
        """

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender


    @classmethod
    def getAPIKey(cls) -> str:
        return cls.getSetting(SettingProp.API_KEY)
