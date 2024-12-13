# -*- coding: utf-8 -*-
from __future__ import annotations  # For union operator |

import io
import sys
from pathlib import Path

from common import *
from backends.audio.sound_capabilities import ServiceType, SoundCapabilities
from backends.players.iplayer import IPlayer
from backends.players.player_index import PlayerIndex
from backends.settings.service_types import Services
from cache.voicecache import CacheEntryInfo, VoiceCache
from common.base_services import BaseServices
from common.logger import *
from common.phrases import Phrase
from common.setting_constants import AudioType
from common.settings import Settings
from common.settings_low_level import SettingsProperties

module_logger = BasicLogger.get_logger(__name__)

"""
Overview:
If caching is enabled, text to be voiced:

First goes to the cache_reader to see if the sound file for the text is in the cache
  If it is in the cache, then it is sent directly to the player
  If not in the cache, then the text is sent to the current engine to voice
  
  If the engine can not voice (due to remote denial of service, etc.)
     then the text is saved as text in the cache:
        1- to prevent from repeatedly trying for the next day
        2- to be able to have other engines or engine configs create sound files prior to
           demand
     next, if an alternate voicing service is configured:
        1- if the alternate voicing service uses another cache, then start over with the
           first step here with the cache reader
        2- if no cache is used, send text directly to the alternate engine
        
Each 'service' in the chain passes setting configuration information, as needed, up
the chain, even if the current service has no direct interest. In general, the consumer
of settings can directly query for the appropriate settings and conversions.

  When voiced text is created and played by an engine without caching, then all of the
  audio settings can be processed at the only stage needed, the engine
  
  However, when voiced text is cached or when it is forwarded to a player, or 
  converted to another format, then every stage prior to the player, will use the
  engine's default settings (or settings which attempts to produce consistent
  results across all of the engines (impossible to get perfectly, but the product is
  better the more consistent the audio is using the same settings across the different
  engines, players, etc.).
           
                                                |-- Not successful --> save text in 
                                                cache --> alt engine
text -> cache_reader --- not found --> engine --- successful ---> voiced_byte_stream -> 
cache_writer  --> player
                   |---- found ---> player
                   

Currently, the 'backend' (aka 'engine') classes are in charge of the general flow and
processing. With the addition to some services, such as caching and background 
pre/post-demand voicing, a different model is needed.

A Driver will be in charge of orchestrating the flow of voicing. service.py will 
interact with Driver to initiate voicing. Driver will be in charge after that. 
Of course Driver will let each sub-service manage it's own concerns, as appropriate.    
               
"""


class BaseCache(BaseServices):
    """
    Communicates with the VoiceCache to handle the cache library services.
    """

    '''
    pitchConstraints: Constraints = Constraints(0, 50, 99, True, False, 1.0,
                                                SettingsProperties.PITCH)
    volumeConstraints: Constraints = Constraints(-12, 8, 12, True, True, 1.0,
                                                 SettingsProperties.VOLUME, midpoint=0)

    # Special Conversion constraint due to max native range is more or less
    # equivalent to 0db. See note in getEngineVolume

    volumeConversionConstraints: Constraints = Constraints(minimum=0.1, default=1.0,
                                                           maximum=2.0, integer=False,
                                                           decibels=False,
                                                           scale=1.0,
                                                           property_name=SettingsProperties.VOLUME,
                                                           midpoint=1,
                                                           increment=0.1)
    #  Note that default native volume is at max. Prefer to use external
    #  player for volume.
    volumeNativeConstraints = Constraints(1, 10, 10, False, True, scale=0.1)
    '''

    settings: Dict[str, str | int | bool] = {
        SettingsProperties.CACHE_PATH: None
    }
    supported_settings: Dict[str, str | int | bool] = settings
    _logger: BasicLogger = None
    _class_name: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        clz = type(self)
        clz._class_name = self.__class__.__name__

        self.process = None
        self.stop_processing = False

    def init(self) -> None:
        clz = type(self)
        if self.initialized:
            return
        super().init()
        self.update()

    @staticmethod
    def isSupportedOnPlatform() -> bool:
        return True

    @staticmethod
    def isInstalled() -> bool:
        return True

    def getVoicedText(self, phrase: Phrase, cache_identifier: str,
                      sound_file_types: List[str]) -> Tuple[str, bool, str]:
        path_to_voiced_file: str
        exists: bool
        file_type: str
        path, exists, file_type = VoiceCache.get_best_path(phrase,
                                                           sound_file_types)
        return path, exists, file_type

    def get_path_to_voice_file(self, text_to_voice: str,
                               use_cache: bool = False) -> Tuple[str, bool]:
        """

        @param text_to_voice:
        @param use_cache:
        @return:
        """
        clz = type(self)
        player_id: str = clz.getSetting(SettingsProperties.PLAYER)
        player: IPlayer = PlayerIndex.get_player(player_id)
        sound_file_types: List[str] = SoundCapabilities.get_input_formats(player_id)
        voice_file: str = ''
        exists: bool = False
        file_type: str = ''
        result: CacheEntryInfo
        result = VoiceCache.get_path_to_voice_file(text_to_voice,
                                                   use_cache)
        voice_file = result.current_voice_path
        if use_cache:
            exists = result.text_exists
        return voice_file, exists

    def get_best_path(self, text_to_voice: str,
                      sound_file_types: List[str]) -> Tuple[str, bool, str]:
        path, exists, file_type = VoiceCache.get_best_path(text_to_voice,
                                                           sound_file_types)
        return path, exists, file_type

    def voiceFile(self, text_to_voice: str, path: str):
        pass

    def voiceByteS(self, text_to_voice, voice: bytes):
        pass

    def create_sound_file(self, voice_file_path: str,
                          sound_file_type: str) -> Tuple[int, IO[io.BufferedWriter]]:

        return VoiceCache.create_sound_file(voice_file_path, sound_file_type)

    def runCommandAndPipe(self, use_cache: bool, text_to_voice: str):
        clz = type(self)

        # If caching disabled, then voice_file and byte_stream are always None.
        # If caching is enabled, voice_file contains path of cached file,
        # or path where to download to. byte_stream is None if cached file
        # does not exist, otherwise it is the contents of the cached file

        self.stop_processing = False
        audio_pipe = None
        voice_file: str | None
        exists: bool
        byte_stream: io.BinaryIO = None
        voice_file, exists = self.get_path_to_voice_file(text_to_voice,
                                                         use_cache)
        if not voice_file or len(voice_file) == 0:
            voice_file = None
        """
        if not text_exists:
            voice_file, _ = self.download_speech(
                    text_to_voice, voice_file)
        try:
            byte_stream = io.open(voice_file, 'rb')
        except Exception:
            clz._logger.exception('')
            byte_stream = None
        """

        # the following a geared towards Mplayer. Assumption is that only adjust
        # volume in player, other settings in engine.

        # volume_db: float = clz.get_volume_db()  # -12 .. 12
        return byte_stream

    def update(self):
        self.process = None
        self.stop_processing = False

    def close(self):
        # self._close()
        pass

    def _close(self):
        # self.stop()
        # super()._close()
        pass

    def stop(self):
        clz = type(self)
        if clz._logger.isEnabledFor(DEBUG_V):
            clz._logger.debug_v('stop')
        self.stop_processing = True
        if not self.process:
            return
        try:
            if clz._logger.isEnabledFor(DEBUG_V):
                clz._logger.debug_v('terminate')
            self.process.terminate()  # Could use self.process.kill()
        except AbortException:
            reraise(*sys.exc_info())
        except:
            pass

    @classmethod
    def isSettingSupported(cls, setting) -> bool:
        if setting in cls.settings.keys():
            return True
        return False

    @classmethod
    def getSettingNames(cls) -> List[str]:
        settingNames: List[str] = []
        for settingName in cls.settings.keys():
            settingNames.append(settingName)

        return settingNames

    @classmethod
    def getSetting(cls, key, default=None):
        """
        Gets a setting from addon's settings.xml

        A convenience method equivalent to Settings.getSetting(key + '.'. +
        cls.service_id,
        default, useFullSettingName).

        :param key:
        :param default:
        :return:
        """
        #  if default is None:
        #      default = cls.get_setting_default(key)

        # It would be better to know the engineId

        return Settings.getSetting(key, default)

    @classmethod
    def settingList(cls, setting, *args) -> List[str]:
        """
        Gets the possible specified setting values in same representation
        as stored in settings.xml (not translate). Sorting/translating done
        in UI.

        :param setting:
        :param args:
        :return:
        """
        if setting == SettingsProperties.LANGUAGE:
            # Returns list of languages and value of closest match to current
            # locale
            pass
        elif setting == SettingsProperties.GENDER:
            pass
        elif setting == SettingsProperties.VOICE:
            pass

    @classmethod
    def getLanguage(cls) -> str:
        language = cls.getSetting(SettingsProperties.LANGUAGE)
        language = 'en-US'
        return language

    @classmethod
    def getGender(cls) -> str:
        gender = 'female'
        return gender


class CacheWriter(BaseCache):

    service_ID: str = Services.CACHE_WRITER_ID
    service_TYPE: str = ServiceType.CACHE_WRITER
    _logger: BasicLogger = None
    _initialized: bool = False

    # Find what engines can produce WAV files.
    _supported_input_formats: List[AudioType] = []
    _supported_output_formats: List[AudioType] = [AudioType.WAV]
    capable_services = SoundCapabilities.get_capable_services(ServiceType.ENGINE,
                                                              _supported_input_formats,
                                                              _supported_output_formats)

    def __init__(self):
        super().__init__()
        clz = type(self)
        if clz._logger is None:
            clz._logger = module_logger
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True

    def saveVoicedBytes(self, path: str, cacheIdentifier: str,
                        voicedBytes: bytes) -> bool:
        pass

    def saveAndForwardVoicedBytes(self, path: str, cache_identifier: str,
                                  voicedBytes: bytes,
                                  service_id: str) -> bool:
        pass


class CacheReader(BaseCache):
    """
      Locates any voice file for the given text
      """
    engine_id: str = Services.CACHE_READER_ID
    service_ID: str = Services.CACHE_READER_ID
    service_TYPE: str = ServiceType.CACHE_READER
    _initialized: bool = False

    def __init__(self):
        super().__init__()
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger
        if not clz._initialized:
            clz.register(self)
            clz._initialized = True

    def findVoicedText(self, text_to_voice: str, cache_identifier: str,
                       forward: bool) -> Tuple[bool, str]:
        # Tuple[found, path]
        pass

    def forwardVoicedbBytes(self, path: str, service_id: str) -> bool:
        pass
