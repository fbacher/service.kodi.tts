# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import sys
from pathlib import Path

import langcodes
from backends import base
from backends.engines.idownloader import OutputType
from backends.engines.piper_api import (PiperApi, PiperData,
                                        PiperDownloader,
                                        PiperModel)
from backends.engines.speech_generator import SpeechGenerator
from backends.ispeech_generator import ISpeechGenerator
from backends.players.iplayer import IPlayer
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.service_types import (EngineType, QualityType, ServiceID,
                                             ServiceKey, Services,
                                             ServiceType)
from backends.settings.setting_properties import SettingProp
from cache.cache_file_state import CacheFileState
from cache.voicecache import VoiceCache
from common import *
from common.base_services import BaseServices
from common.constants import Constants
from common.logger import *
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

    lang_info_map: Dict[str, 'LangInfo'] = {}
    initialized: bool = False
    voices_initialized_initialized: bool = False
    global_lang_initalized: bool = False
    lang_limit: int = 0
    MAX_LANG_LIMIT: int = 5

    @classmethod
    def load_voices(cls):
        """
        Converts Piper's Model information into Voice Groups and Voices.
        :return:
        """
        MY_LOGGER.debug(f'load_voices')
        if not cls.initialized:
            cls.initialized = True
            # User can only choose a voice that belongs to the current major
            # language
            current_language: str = langcodes.Language.get(Constants.LOCALE).language
            engine_quality: int = EngineType.PIPER.ordinal

            #  TODO: Change keep_definitions so that it is controlled by user in UI

            p_models: List[PiperModel]
            p_models = PiperApi.get_tts_voice_details(current_language,
                                                      include_uninstalled=True,
                                                      keep_definitions=True)
            """
            A p_model contains information about a Piper Model which describes
            a group of voices. The UI will present the group as well as the voices
            within it. The models are not necessarily downloaded. For those not 
            downloaded all of the information is derived from the model's name. 
            The primary thing missing is information about the model's voices.
            Once a user chooses to explore a model it will be downloaded along
            with the voice information.            
            """
            for v_group in p_models:
                v_group: PiperModel
                # MY_LOGGER.debug(f'v_group: {v_group.vg_label}')
                ietf_lang: langcodes.Language
                try:
                    # We are only interested in the current language (i.e. "en")
                    if v_group.language.language != current_language:
                        continue
                    # Add the language variant (en_US vs en_GB). Dupes will be ignored
                    ietf_tag: str = v_group.language.to_tag()
                    engine_ietf_tag: str = PiperModel.current_ietf_tag
                    EngineVoiceManager.add_language(engine_key=PiperTTSEngine.service_key,
                                                    ietf_tag=ietf_tag,
                                                    engine_lang_id=engine_ietf_tag)
                except AbortException:
                    reraise(*sys.exc_info())
                except LanguageTagError:
                    MY_LOGGER.exception('')

            cls.load_speakers(p_models)

    @classmethod
    def start_http_server(cls):
        pass


    @classmethod
    def load_speakers(cls, p_models: List[PiperModel]) -> None:
        """
        Get all supported languages from piper. Using 'langcodes', convert
        them into standard IETF format, get translated names, etc.... Finally,
        hand off the entries to Kodi TTS.

        :param p_models: Contains information about Piper Models, which become
                         Voice Groups
        :return: None
        """
        if not cls.voices_initialized_initialized:
            cls.voices_initialized_initialized = True

            #  Each entry represents a voice group with one or more voices

            for v_group in p_models:
                v_group: PiperModel
                # The vg_id always refers to the filename prefix describing the
                # voice group.
                #
                # The v_label refers to either the name of the single voice
                # of the voice group, or one of the speakers in the group.
                #
                # The voice_id refers to the index of a defined voice, or
                # zero when there are no defined speakers, or '', when
                # the entry is for the group description preceding the voice
                # entries.
                vg_id: str = v_group.vg_id
                voice_quality: QualityType = v_group.quality
                try:
                    if False:
                        MY_LOGGER.debug(f'engine_key: {PiperTTSEngine.service_key}\n'
                                        f'ietf_tag: {locale_id}\n'
                                        f'gender: {Genders.ANY}\n'
                                        f'default_voice_id: {speaker_id}\n'
                                        f'engine_lang_id: {lower_locale_id}\n'
                                        f'e_vg_id: {vg_id}\n'
                                        f'quality: {voice_quality.label}\n'
                                        f'vg_label: {vg_name}\n'
                                        f'speaker_name: {speaker_name}\n'
                                        f'voice_name: {voice_name}\n'
                                        f'voice_id: {speaker_id}'
                                        f'vg_id: {vg_id}')

                    if False:  #  MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'VOICE GROUP\n'
                                    f'engine_key: {PiperTTSEngine.service_key}\n'
                                    f'ietf_tag: {locale_id}\n'
                                    f'gender: {Genders.ANY}\n'
                                    f'default_voice_id: {speaker_id}\n'
                                    f'engine_lang_id: {lower_locale_id}\n'
                                    f'e_vg_id: {vg_id}\n'
                                    f'quality: {voice_quality.label}\n'
                                    f'vg_label: {v_group.vg_label}')
                        MY_LOGGER.debug_v(f'vg_name: {v_group.vg_name}')
                    EngineVoiceManager.add_voice_group(
                            engine_key=PiperTTSEngine.service_key,
                            ietf_tag=v_group.language.to_tag(),
                            gender=Genders.ANY,
                            default_voice_id='0',
                            engine_lang_id=PiperModel.current_ietf_tag.lower(),
                            engine_vg_id=vg_id,
                            voice_quality=voice_quality,
                            vg_label=v_group.vg_label,
                            model_present=v_group.model_present)
                    if False:  # if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'VOICE\n'
                                    f'engine_key: {PiperTTSEngine.service_key}\n'
                                    f'ietf_tag: {locale_id}\n'
                                    f'gender: {Genders.ANY}\n'
                                    f'engine_lang_id: {lower_locale_id}\n'
                                    f'e_voice_id: {speaker_id}\n'
                                    f'e_vg_id: {vg_id}\n'
                                    f'quality: {voice_quality.label}\n'
                                    f'voice_label: {voice_name}')

                    for v_name, v_id in v_group.voice_id_map.items():
                        v_name: str
                        v_id: int
                        EngineVoiceManager.add_voice(
                                engine_key=PiperTTSEngine.service_key,
                                ietf_tag=v_group.language.to_tag(),
                                gender=Genders.ANY,
                                engine_lang_id=PiperModel.current_ietf_tag.lower(),
                                e_voice_id=f'{v_id}',
                                real_voice_id=f'{v_id}',
                                engine_vg_id=vg_id,
                                voice_quality=voice_quality,
                                voice_label=v_name)
                        if MY_LOGGER.isEnabledFor(DEBUG_XV):
                            MY_LOGGER.debug_xv(f'{vg_id} new_voice: {v_name} v_id: {v_id}')
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

        MY_LOGGER.debug(f'In PiperTTSEngine.init')

        PiperApi.init_piper_data()

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
                    MY_LOGGER.debug(f'vg_id: {vg_id} vg: {vg.e_vg_id}')
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
            -> ISpeechGenerator:
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
        MY_LOGGER.debug(f'cache_file_state: {cache_file_state} phrase: {phrase} '
                        f'{phrase.cache_path}')
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
