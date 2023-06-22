"""
Classes which orchestrates the voicing of text.

Basically a request comes in to voice some text

 say "" ->
"""
import sys

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
from common.setting_constants import Mode, Players
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

    def say(self, text: str, interrupt: bool = False,
            preload_cache: bool = False) -> None:
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

        clz = type(self)
        Monitor.throw_exception_if_abort_requested(0.05)
        try:
            result: Result = None
            mode: Mode
            engine_id: str = Settings.get_engine_id()
            active_engine: BaseEngineService
            if engine_id is None:
                clz._logger.debug(f'engine_id is not set')
                return
            active_engine = BaseServices.getService(engine_id)
            if active_engine is None:
                clz._logger.debug(f'invalid active_engine engine_id: {engine_id}')
                return
            if interrupt:
                active_engine._stop()

            player_id: str = Settings.get_player_id(engine_id)

            # self.tts.say(self.cleanText(text), interrupt, preload_cache)

            # active_engine.say(text, interrupt, preload_cache)
            # return

            if player_id == Players.INTERNAL:
                mode = Mode.ENGINESPEAK
            elif Settings.uses_pipe(engine_id):
                mode = Mode.PIPE
            else:
                mode = Mode.FILEOUT
            # Ensure player has been initialized

            converter_id: str = self.getConverter_for(engine_id)
            if converter_id is None:
                if player_id is None or len(player_id) == 0:
                    player_id = None
                else:
                    # Forces initialization and populates capabilities, settings, etc.

                    player: IPlayer = PlayerIndex.get_player(player_id)
                    player_input_formats: List[str]
                    player_input_formats = SoundCapabilities.get_input_formats(player_id)
                    if not SoundCapabilities.MP3 in player_input_formats:
                        pass

            if active_engine.is_use_cache():
                if not self.say_cached_file(active_engine, player_id, text):
                    self.generate_voice(active_engine, text)
                # else:
                #    self.handle_caching(text, engine_id, player_id, converter_id)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

    def stop(self):
        clz = type(self)
        try:
            engine_id: str = Settings.get_engine_id()
            active_engine = BaseServices.getService(engine_id)
            active_engine.stop()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

    def close(self):
        clz = type(self)
        try:
            engine_id: str = Settings.get_engine_id()
            active_engine = BaseServices.getService(engine_id)
            active_engine.close()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

    def isSpeaking(self) -> bool:
        clz = type(self)
        try:
            engine_id: str = Settings.get_engine_id()
            active_engine = BaseServices.getService(engine_id)
            return active_engine.isSpeaking()
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return False

        # tts.dead
        # tts.deadReason

    def sayList(self, texts, interrupt: bool = False):
        """Accepts a list of text strings to be spoke

        May be overriden by subclasses. The default i
        for each item in texts, calling insertPause()
        If interrupt is True, the subclass should int
        """
        clz = type(self)
        try:
            self.say(texts.pop(0), interrupt=interrupt)
            for t in texts:
                self.say(t, pause_ms=500)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

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
        Monitor.throw_exception_if_abort_requested(timeout=0.05)
        clz = type(self)
        cached_file: str = ''
        exists: bool = False
        try:
            cached_file, exists = active_engine.get_path_to_voice_file(text,
                                                                       use_cache=True)
            if exists:
                return self.say_file(active_engine, player_id, cached_file)
            return False
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return False

    def generate_voice(self, active_engine: BaseEngineService, text: str) -> None:
        Monitor.throw_exception_if_abort_requested(timeout=0.01)
        clz = type(self)
        try:
            player_id: str = SettingsMap.get_value(active_engine.service_ID,
                                                   SettingsProperties.PLAYER)

            # Forces initialization and populates capabilities, settings, etc.

            player: IPlayer = PlayerIndex.get_player(player_id)
            if player_id == Services.INTERNAL_PLAYER_ID:
                pass
            else:
                active_engine.say(text, interrupt=False, preload_cache=False)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')

    def say_file(self, active_engine: BaseEngineService, player_id: str,
                 voice_file) -> bool:
        clz = type(self)
        try:
            # negotiate player/converter, etc.
            tts_data: TTSQueueData = TTSQueueData(None, state='play_file',
                                                  player_id=player_id,
                                                  voice_file=voice_file,
                                                  engine_id=active_engine.service_ID)

            self.worker_thread.add_to_queue(tts_data)
            return True
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return False

    def getConverter_for(self, engine_id: str) -> str | None:
        clz = type(self)
        Monitor.throw_exception_if_abort_requested(0.05)
        try:
            converter_id: str = Settings.get_setting_str(SettingsProperties.CONVERTER,
                                                         engine_id, ignore_cache=False,
                                                         default_value=None)
            engine_produces_audio_types: List[str]
            engine_produces_audio_types = SoundCapabilities.get_output_formats(engine_id)
            if SoundCapabilities.MP3 in engine_produces_audio_types:
                # No converter needed, need to check player
                return None

            eligible_converters: List[str]
            eligible_converters = SoundCapabilities.get_capable_services(ServiceType.CONVERTER,
                                                      [SoundCapabilities.WAVE],
                                                      engine_produces_audio_types)
            converter_id = None
            if len(eligible_converters) > 0:
               converter_id = eligible_converters[0]
            else:
                converter = self.getService(converter_id)
            return converter_id
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
        return None

    def prefetch(self, text: str, background: bool) -> None:
        pass

    def getBackendSetting(self, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. + cls.backend_id,
        default, useFullSettingName).False

        :param key:
        :param default:
        :return:
        """
        current_backend: ITTSBackendBase = BackendInfoBridge.getBackend()
        if default is None:
            default = current_backend.get_setting_default(key)

    def handle_caching(self, text: str, engine_id: str, player_id: str, converter_id: str):
        clz = type(self)
        Monitor.throw_exception_if_abort_requested(0.01)
        try:
            if converter_id is not None and len(converter_id) > 0:
                converter_output_formats: List[str]
                converter_output_formats = SoundCapabilities.get_output_formats(converter_id)
            player_input_formats: List[str]
            player_input_formats = SoundCapabilities.get_input_formats(player_id)

            file_type: str = ''
            path, exists, file_type = self.cache_reader.getVoicedText(text, cache_identifier='',
                                                                sound_file_types=player_input_formats)
            if exists:
                player: IPlayer = PlayerIndex.get_player(player_id)
                player.init(engine_id)
                player.play(path)
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            clz._logger.exception('')
