"""
Classes which orchestrates the voicing of text.

Basically a request comes in to voice some text

 say "" ->
"""
from backends.audio.sound_capabilties import SoundCapabilities
from backends.audio.worker_thread import TTSQueue, TTSQueueData, WorkerThread
from backends.backend_info_bridge import BackendInfoBridge
from backends.base import BaseEngineService
from backends.cache_writer import CacheReader
from backends.i_tts_backend_base import ITTSBackendBase
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.logger import BasicLogger
from common.minimal_monitor import MinimalMonitor
from common.monitor import Monitor
from common.settings import Settings
from common.settings_low_level import SettingsProperties
from common.typing import *

module_logger: BasicLogger = BasicLogger.get_module_logger(module_path=__file__)


class Result:
    def __init__(self):
        pass


class Driver(BaseServices):

    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger.getChild(self.__class__.__name__)
            self.worker_thread: WorkerThread = WorkerThread('worker', task=None)
            self.cache_reader = CacheReader()

    def say(self, text: str) -> None:
        """
        Initiates multi-step process to voice some text
         1) Determine engine used
         2) Determine if it supports caching of voiced files
         3) if supports caching, then run check engine's cache for entry for text
            if found, skip having engine generate new voicing
            else
            4) run engine to produce voice file to add to cache
            if engine does not produce audio file-type configured for cache,
            then run converter, such as mplayer to convert (probably from wav to
            mpeg3)
            5) play audio from cache
         6 else if no caching
           if engine is also the player to use, then have engine voice and play text
           else, have engine voice text and save to temp
           ...

        :param text: Text to voice
        """
        # Initiates typically multi-step process to voice some text

        MinimalMonitor.throw_exception_if_abort_requested(0.0)
        result: Result = None
        engine_id: str = Settings.get_engine_id()
        active_engine: BaseEngineService
        active_engine = BaseServices.getService(engine_id)
        player_id: str = Settings.get_setting_str(SettingsProperties.PLAYER, engine_id)
        # Ensure player has been initialized

        converter_id: str = self.getConverter_for(engine_id)
        if converter_id is None:
            if player_id is None or len(player_id) == 0:
                player_id = None
            else:
                # Forces initialization and populates capabilities, settings, etc.

                player: IPlayer = PlayerIndex.get_player(player_id)
                player_sound_capabilities: SoundCapabilities
                player_sound_capabilities = SoundCapabilities.get_by_service_id(player_id)
                if not SoundCapabilities.MP3 in player_sound_capabilities.supported_input_formats:
                    player_sound_capabilities = None
        if Settings.is_use_cache(engine_id):
            if not self.say_cached_file(active_engine, player_id, text):
                result = self.generate_voice(active_engine, text)

        if Settings.getSetting(SettingsProperties.CACHE_SPEECH, engine_id):
            self.handle_caching(text, engine_id, player_id, converter_id)

    def say_cached_file(self, active_engine: BaseEngineService, player_id: str,
                        text: str) -> bool:
        """
        Check to see if text is in cache of voiced files for this engine. If so,
        then say the voice file
        :param text:
        :param active_engine:
        :param player_id:
        :return:
        """
        MinimalMonitor.throw_exception_if_abort_requested(timeout=0.0)
        cached_file: str
        exists: bool
        cached_file, exists = active_engine.get_path_to_voice_file(text,
                                                                   use_cache=True)
        if exists:
            return self.say_file(active_engine, player_id, cached_file)
        return False

    def generate_voice(self, active_engine: BaseEngineService, text: str) -> Result:
        MinimalMonitor.throw_exception_if_abort_requested(timeout=0.01)

        player_id: str = SettingsMap.get_value(active_engine.service_ID,
                                               SettingsProperties.PLAYER)

        # Forces initialization and populates capabilities, settings, etc.

        player: IPlayer = PlayerIndex.get_player(player_id)
        if player_id == Services.INTERNAL_PLAYER_ID:
            pass
        else:
            active_engine.say(text, interrupt =False, preload_cache=False)

    def say_file(self, active_engine: BaseEngineService, player_id: str,
                 voice_file) -> bool:
        # negotiate player/converter, etc.
        tts_data: TTSQueueData = TTSQueueData(None, state='play_file',
                                              player_id=player_id,
                                              voice_file=voice_file,
                                              engine_id=active_engine.service_ID)

        self.worker_thread.add_to_queue(tts_data)

        return True

    def getConverter_for(self, engine_id: str) -> str | None:
        MinimalMonitor.throw_exception_if_abort_requested(0)
        converter_id: str = Settings.get_setting_str(SettingsProperties.CONVERTER, engine_id)
        if converter_id is None or len(converter_id) == 0:
            engine_sound_capabilities = SoundCapabilities.get_by_service_id(engine_id)
            if engine_sound_capabilities.is_supports_output_format(SoundCapabilities.MP3):
                # No converter needed, need to check player
               return None

            engine_produces_audio_types: List[str] = \
                engine_sound_capabilities.supportedOutputFormats()
            candidate_converters: List[SoundCapabilities] = \
                engine_sound_capabilities.get_candidate_consumers(ServiceType.CONVERTER,
                                                                  SoundCapabilities.MP3,
                                                                  engine_produces_audio_types)
            converter_id = None
            if len(candidate_converters) > 0:
                converter_id = candidate_converters[0].service_id
        else:
            converter = self.getService(converter_id)
        return converter_id

    def prefetch(self, text: str, background: bool) -> None:
        pass

    def getBackendSetting(self, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls.backend_id,
        default, useFullSettingName).

        :param key:
        :param default:
        :return:
        """
        current_backend: ITTSBackendBase = BackendInfoBridge.getBackend()
        if default is None:
            default = current_backend.get_setting_default(key)

    def handle_caching(self, text: str, engine_id: str, player_id: str, converter_id: str):
        clz = type(self)
        MinimalMonitor.throw_exception_if_abort_requested(0.0)
        try:
            if converter_id is not None and len(converter_id) > 0:
                converter_sound_capabilities: SoundCapabilities = None
                converter_sound_capabilities = SoundCapabilities.get_by_service_id(converter_id)
                converter_output_formats: List[str] = \
                    converter_sound_capabilities.supported_output_formats
            player_sound_capabilities: SoundCapabilities = None
            player_sound_capabilities = SoundCapabilities.get_by_service_id(player_id)
            player_sound_formats: List[str] = player_sound_capabilities.supported_input_formats

            file_type: str = ''
            path, exists, file_type = self.cache_reader.getVoicedText(text, cache_identifier='',
                                                                sound_file_types=player_sound_formats)
            if exists:
                pass
        except Exception as e:
            clz._logger.exception('')
