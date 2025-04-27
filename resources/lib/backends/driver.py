# coding=utf-8
from __future__ import annotations  # For union operator |

from pathlib import Path

from backends.ispeech_generator import ISpeechGenerator
from backends.settings.service_unavailable_exception import ServiceUnavailable
from cache.cache_file_state import CacheFileState

"""
Classes which orchestrates the voicing of text.

Basically a request comes in to voice some text

 say "" ->
"""
import sys

from common import *

from backends.audio.sound_capabilities import SoundCapabilities
from backends.audio.worker_thread import TTSQueueData, WorkerThread
from backends.backend_info_bridge import BackendInfoBridge
from backends.base import BaseEngineService
from backends.cache_writer import CacheReader
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import ServiceID, Services, ServiceType
from backends.settings.settings_map import SettingsMap
from cache.voicecache import VoiceCache
from cache.common_types import CacheEntryInfo
from common.base_services import BaseServices
from common.exceptions import ExpiredException
from common.logger import *
from common.monitor import Monitor
from common.phrases import Phrase, PhraseList, PhraseUtils
from common.setting_constants import AudioType, Mode
from common.settings import Settings
from common.settings_low_level import SettingProp

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class Result:

    def __init__(self):
        pass


class Driver(BaseServices):
    _initialized: bool = False

    def __init__(self):
        clz = type(self)
        if not clz._initialized:
            self.worker_thread: WorkerThread = WorkerThread('worker',
                                                            task=None)
            self.cache_reader = CacheReader()
            clz._initialized = True
        super().__init__()

    def say(self, phrases: PhraseList) -> None:
        """
        Initiates multi-step process to voice some phrases
         1) Determine engine used
         2) Determine if it supports caching of voiced files
         3) if supports caching, then run check engine's cache for entry for phrase
            if found, skip having engine generate new voicing
            else
            4) run engine to produce voice file to add to cache
            if engine does not produce audio file-type configured for cache,
            then run converter, such as mplayer to convert (probably from wav to
            mp3)
            5) play audio from cache
         6 else if no caching
           if engine is also the player_key to use, then have engine voice and play text
           else, have engine voice text and save to temp
           ...

        :param phrases: Text to voice
        """
        # Initiates typically multi-step process to voice some text

        clz = type(self)
        Monitor.exception_on_abort(0.05)
        active_engine: BaseEngineService | None = None
        try:
            result: Result | None = None
            mode: Mode
            engine_servc_id: ServiceID = Settings.get_engine_key()
            #  MY_LOGGER.debug(f'engine_servc_id: {engine_servc_id}')
            if engine_servc_id is None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine_servc_id is not set')
                return
            try:
                active_engine = BaseServices.get_service(engine_servc_id)
            except ServiceUnavailable:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'invalid active_engine engine_servc_id: '
                                    f'{engine_servc_id}')
                return
            if engine_servc_id.service_id != active_engine.service_id:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'service_key: {engine_servc_id} active_engine: '
                                    f'{active_engine.service_id}')
            try:
                if phrases.interrupt:  # Interrupt should only be on first phrase
                    phrases.add_event('driver.say')
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'INTERRUPT Driver.Say {phrases[0].get_text()}')
                    phrases.expire_all_prior()
                    # self.worker_thread.interrupt()
            except ExpiredException:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug('Expired at Interrupt')

            player_key: ServiceID = Settings.get_player_key(engine_servc_id)
            try:
                phrase: Phrase | None = None
                success: bool = True
                phrase_idx: int = -1
                for phrase in phrases:
                    phrase_idx += 1
                    interrupt: str = ''
                    if phrase.get_interrupt():
                        interrupt = 'INTERRUPT'
                    '''
                    ALL text to be voiced, must be kept synchronized by going
                    through queues. Otherwise things will get scrambled.
                    '''
                    if Settings.is_use_cache():
                        active_engine.update_voice_path(phrase)
                        voice_path: Path
                        suffixes: List[str]
                        phrase.update_cache_path(active_engine)

                    # Save text to .txt file so that background thread can convert
                    # text when there is time (like while idle or watching a movie).
                    # This greatly speeds up building a large set of voice files,
                    # which, in turn, greatly improves responsiveness.
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'cache: {Settings.is_use_cache()} '
                                        f'active generator: '
                                        f'{active_engine.has_speech_generator()}')
                    if (Settings.is_use_cache()
                            and phrase.cache_file_state() != CacheFileState.OK
                            and active_engine.has_speech_generator()):
                        # Clone phrases to seed voice cache
                        phrases_new: PhraseList = PhraseList(check_expired=False)
                        phrase_new: Phrase = phrase.clone(check_expired=False)
                        phrases_new.append(phrase_new)
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'Seeding, active_engine: '
                                            f'{active_engine.service_id}')
                        self._seed_text_cache(active_engine, phrases_new)
                        # Mark original phrase as being downloaded
                        phrase.set_download_pending()
                        '''
                        generator: ISpeechGenerator
                        generator = active_engine.create_speech_generator()
                        generator.generate_speech(phrase, timeout=0.0)
                        '''

                    tts_data: TTSQueueData
                    tts_data = TTSQueueData(None, state='play_file',
                                            player_key=player_key,
                                            phrase=phrase,
                                            engine_key=active_engine.service_key)
                    # MY_LOGGER.debug(f'player_key: {player_key} '
                    #                 f'engine_servc_id: {engine_servc_id} '
                    #                 f'engine_key: {active_engine.service_key}')
                    self.worker_thread.add_to_queue(tts_data)

            except ExpiredException:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'Expired')
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def stop(self):
        clz = type(self)
        try:
            engine_key: ServiceID = Settings.get_engine_key()
            active_engine = BaseServices.get_service(engine_key)
            active_engine.stop()
        except AbortException:
            reraise(*sys.exc_info())
        except ServiceUnavailable:
            pass
        except Exception as e:
            MY_LOGGER.exception('')

    def close(self):
        clz = type(self)
        try:
            engine_key: ServiceID = Settings.get_engine_key()
            active_engine = BaseServices.get_service(engine_key)
            active_engine.close()
        except AbortException:
            reraise(*sys.exc_info())
        except ServiceUnavailable:
            pass
        except Exception as e:
            MY_LOGGER.exception('')

    def isSpeaking(self) -> bool:
        clz = type(self)
        try:
            engine_key: ServiceID = Settings.get_engine_key()
            active_engine = BaseServices.get_service(engine_key)
            return active_engine.is_speaking()
        except AbortException:
            reraise(*sys.exc_info())
        except ServiceUnavailable:
            # Should not occur for the active engine.
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.exception(f'Active engine is ServiceUnavailable')
            return False
        except Exception as e:
            MY_LOGGER.exception('')
        return False

        # tts.dead
        # tts.deadReason

    def say_cached_file(self, active_engine: BaseEngineService, player_key: ServiceID,
                        phrase: Phrase) -> bool:
        """
        Check to see if text is in cache of voiced files for this engine. If so,
        then say the voice file
        :param phrase:
        :param active_engine:
        :param player_key:
        :return:
        """
        Monitor.exception_on_abort(timeout=0.05)
        clz = type(self)
        cached_file: str = ''
        exists: bool = False
        try:
            if phrase.get_cache_path is None:
                result: CacheEntryInfo
                result = VoiceCache.get_path_to_voice_file(phrase, use_cache=True)
            if phrase.text_exists(active_engine):
                return self.say_file(active_engine, player_key, phrase)
            return False
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('Expired')
            return True
        except Exception as e:
            MY_LOGGER.exception('')
        return False

    def _seed_text_cache(self, active_engine: BaseEngineService,
                         phrases_arg: PhraseList) -> None:
        clz = type(self)
        Monitor.exception_on_abort(timeout=0.01)
        try:
            # We don't care about expiration
            phrases: PhraseList
            phrases = phrases_arg.clone(check_expired=False)
            phrases_arg.add_event('driver.seed_text')
            if MY_LOGGER.isEnabledFor(INFO):
                MY_LOGGER.info(f'seed_cache: engine: {active_engine}')
            tts_data: TTSQueueData = TTSQueueData(None, state='seed_cache',
                                                  phrases=phrases,
                                                  engine_key=active_engine.service_key)

            self.worker_thread.add_to_queue(tts_data)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')

    def generate_voice(self, active_engine: BaseEngineService, phrase: Phrase) -> None:
        Monitor.exception_on_abort(timeout=0.01)
        clz = type(self)
        try:
            player_id: str = SettingsMap.get_value(active_engine.service_key,
                                                   SettingProp.PLAYER)
            # Forces initialization and populates capabilities, settings, etc.

            player: IPlayer = PlayerIndex.get_player(player_id)
            if player_id == Services.BUILT_IN_PLAYER_ID:
                pass
            else:
                phrases: PhraseList = PhraseList()
                phrases.append(phrase)
                active_engine.say(phrases)
        except AbortException:
            reraise(*sys.exc_info())
        except ExpiredException:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Expired')
        except Exception as e:
            MY_LOGGER.exception('')

    def say_file(self, active_engine: BaseEngineService, player_id: ServiceID,
                 phrase: Phrase) -> bool:
        clz = type(self)
        try:
            self.generate_voice(active_engine, phrase)
            return True
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        return False

    def prefetch(self, text: str, background: bool) -> None:
        pass
