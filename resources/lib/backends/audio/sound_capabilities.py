# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

from backends.settings.settings_map import SettingsMap
from common.monitor import Monitor
from common.setting_constants import AudioType, PlayerMode
from backends.settings.service_types import ServiceID, TTS_Type

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
'''
    Helper to exchange audio related information between players, engines
    and anything else that can produce, consume or transform audio.
'''
from common import *

from backends.settings.service_types import Services, ServiceType
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class AudioTypes:
    def __init__(self, audio_types: List[AudioType]) -> None:
        self._has_mp3: bool = False
        self._has_wav: bool = False
        self._has_builtin: bool = False
        if AudioType.WAV in audio_types:
            self._has_wav = True
        if AudioType.MP3 in audio_types:
            self._has_mp3 = True
        if AudioType.BUILT_IN in audio_types:
            self._has_builtin = True

    def common(self, other: AudioTypes) -> AudioTypes:
        common_audio_types: AudioTypes = AudioTypes([])
        if self.has_mp3 and other.has_mp3:
            common_audio_types._has_mp3 = True
        if self.has_wav and other.has_wav:
            common_audio_types._has_wav = True
        if self.has_builtin and other.has_builtin:
            common_audio_types._has_builtin = True
        return common_audio_types

    @property
    def has_builtin(self) -> bool:
        return self._has_builtin

    @property
    def has_mp3(self) -> bool:
        return self._has_mp3

    @property
    def has_wav(self) -> bool:
        return self._has_wav


class SoundCapabilities:
    """
        Helper class to exchange audio related information between players, engines
        and anything else that can produce, consume or transform audio.
    """

    # Sound capabilities are used by engines (which only produce), players
    # (which can play or sometimes convert and play) or converters, which
    # perform some manipulation of the audio and pass it on to its consumer
    # _all_service_capabilites keeps a map of the capabilities of all services

    _capabilities_by_service: Dict[str, Tuple[List[str], List[AudioType]]] = {}
    _services_by_service_type: Dict[ServiceType, Dict[str, None]] = {}

    @classmethod
    def add_service(cls, service_key: ServiceID,
                    service_types: List[ServiceType],
                    supported_input_formats: List[AudioType],
                    supported_output_formats: List[AudioType]) -> None:
        """
        :param service_key: Uniquely identifies the engine, player or converter that
                these capabilities belong to (ex: 'player.mpv.id', 'engine.google.id')
        :param service_types: services which this provides (ServiceType.PLAYER,
                              ServiceType.ENGINE, etc.)
        :param supported_input_formats: ex: mp3, wav
        :param supported_output_formats: mp3, wav
        """
        if not SettingsMap.is_available(service_key):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'service: {service_key} is NOT available, adding anyway')

        # Multiple ServicesTypes is most useful for players, which may also be able
        # to act as a Transcoder (mpv can play or transcode)
        for service_type in service_types:
            service_type: ServiceType
            services_in_type: Dict[str, None]
            # services_in_type means the different kinds of engines or players or
            # transcoders are there.
            services_in_type = cls._services_by_service_type.setdefault(service_type, {})
            services_in_type[service_key.service_id] = None

        if cls._capabilities_by_service.get(service_key.service_id) is None:
            cls._capabilities_by_service[service_key.service_id] = \
                (supported_input_formats, supported_output_formats)

    @classmethod
    def remove_service(cls, service_key: ServiceID,
                       service_types: List[ServiceType]) -> None:
        """
        Removes a service, most likely because it is broken or otherwise not
        available for use

        :param service_key: Uniquely identifies the engine, player or converter
                (ex: 'mpv', 'google')
        :param service_types: type of services provided (ServiceType.PLAYER,
                              ServiceType.ENGINE, etc.)
        :return:
        """
        if not SettingsMap.is_available(service_key):
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'service: {service_key}'
                                f' is NOT available. removing service')
        for service_type in service_types:
            services_in_type: Dict[str, None]
            services_in_type = cls._services_by_service_type.get(service_type)
            if services_in_type is not None:
                del cls._services_by_service_type.get[service_type]

        entry = cls._capabilities_by_service.get(service_key.service_id, None)
        if entry is not None:
            del cls._capabilities_by_service[service_key.service_id]

    @classmethod
    def get_output_formats(cls, service_key: ServiceID) -> List[AudioType]:
        output_formats: List[AudioType]
        _, output_formats = cls._capabilities_by_service[service_key.service_id]
        return output_formats

    @classmethod
    def get_input_formats(cls, service_key: ServiceID,
                          usable_audio_types: AudioTypes) -> List[AudioType]:
        input_formats: List[AudioType]
        input_formats, _ = cls._capabilities_by_service[service_key.service_id]
        input_audio_types: AudioTypes = AudioTypes(input_formats)
        common_audio_types: AudioTypes = input_audio_types.common(usable_audio_types)
        return input_formats

    @classmethod
    def get_capable_services(cls, service_type: ServiceType,
                             consumer_formats: List[AudioType] | AudioType | None = None,
                             producer_formats: List[AudioType] | AudioType | None = None)\
            -> List[ServiceID]:
        """
        TODO: Change to return ServiceType, List[setting_id]
              Should return services which can consume or transform one of the
              input (consumer) formats blah blah
        Returns services which meet the given criteria.

        :param service_type: Input service stage. ex: engine, player, converter, etc.
               None means the service type will be ignored
        :param consumer_formats: audio formats that this service must consume from
               the previous service
               An empty list means that the output audio format will be ignored
        :param producer_formats: preferred/is_required formats that the current service
               should produce. An empty list means that there are no restrictions
        :return:

        Note that the producer_formats field will usually be empty.

        The order is determined by 1) the order of preferred producer formats by
        this service and 2) the order of desired formats produced by this stage.
        """

        """
        A chain of tools is is_required to voice text:
        examples: engine -> wav -> player
                  engine -> wav -> converter -> .mp3 -> cache -> player
                  cache -> mp3 -> player
                    
        The job of this module is to determine the candidate tools for the next stage
        in a sequence. For example, if we are at the engine stage that produces wave
        and we next need to play the sound, then we need a player that can play wave,
        or a converter to mp3 then a player.
        
        The major determinant is whether caching is used or not. If caching is used, 
        then mp3 is is_required (much smaller files). Otherwise, may as well do everything
        in wave since it requires less cpu.
        """
        if consumer_formats is None:
            consumer_formats = []
        elif isinstance(consumer_formats, AudioType):
            consumer_formats = [consumer_formats]
        elif not isinstance(consumer_formats, list):
            MY_LOGGER.exception('Consumer not an AudioType nor list of AudioType')
            raise ValueError('Consumer not an AudioType nor list of AudioType')
        if producer_formats is None:
            producer_formats = []
        elif isinstance(producer_formats, AudioType):
            producer_formats = [producer_formats]
        elif not isinstance(producer_formats, list):
            MY_LOGGER.exception('producer not an AudioType nor list of AudioType')
            raise ValueError('Producer not an AudioType nor list of AudioType')
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'service_type: {service_type}')
            MY_LOGGER.debug(f'consumer_formats: {consumer_formats}')
            MY_LOGGER.debug(f'producer_formats: {producer_formats}')
        services_of_this_type: Dict[str, None]
        services_of_this_type = cls._services_by_service_type.get(service_type)
        if services_of_this_type is None:
            services_of_this_type = {}
        # Now, narrow down this list to the ones that can fulfill consumer/producer
        # requirements

        eligible_services: List[ServiceID] = []
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'services_of_this_type: {services_of_this_type.keys()}')
        for service_id in services_of_this_type.keys():
            service_id: str
            input_formats: List[AudioType]
            output_formats: List[AudioType]

            input_formats, output_formats = cls._capabilities_by_service[service_id]
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'setting_id: {service_id} input_formats: {input_formats}')
                MY_LOGGER.debug(f'output_formats: {output_formats}')
            supports_consumer: bool = False
            if len(consumer_formats) == 0:  # When no consumer then any is acceptable
                supports_consumer = True
            else:
                for audio_format in consumer_formats:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'audio_format: {audio_format}')
                    if (audio_format in input_formats or
                            AudioType.BUILT_IN in input_formats):
                        supports_consumer = True
                        break

            supports_producer: bool = False
            if len(producer_formats) == 0:
                supports_producer = True
            else:
                for audio_format in producer_formats:
                    if audio_format in output_formats:
                        supports_producer = True
                        break
                    for output_format in output_formats:
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'output_format: {output_format}')
                            MY_LOGGER.debug(f'audio_format: {audio_format}')
            if supports_consumer and supports_producer:
                eligible_services.append(ServiceID(service_type, service_id,
                                                   TTS_Type.SERVICE_ID))
        return eligible_services

    @staticmethod
    def get_transcoder(service_key: ServiceID,
                       target_audio: AudioType = AudioType.MP3) -> ServiceID | None:
        """
        Finds a transcoder for the given service based upon its preference,
        availability and Transcoder preference

        :param service_key:
        :param target_audio: MP3 or WAVE
        :return: TransCoderType of found transcoder
                 or None if transcoder not neeeded
                 or ValueError if transcoder could not be found
        """
        Monitor.exception_on_abort(0.05)
        try:
            # converter_id: str = Settings.get_setting_str(SettingProp.TRANSCODER,
            #                                              setting_id, ignore_cache=False,
            #                                              default=None)
            audio_types: List[AudioType]
            audio_types = SoundCapabilities.get_output_formats(service_key)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{service_key} output_formats: {audio_types}')
            if target_audio in audio_types:
                return None  # No converter needed

            eligible_converters: List[ServiceID]
            eligible_converters = \
                SoundCapabilities.get_capable_services(ServiceType.TRANSCODER,
                                                       audio_types,
                                                       AudioType.MP3)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'eligible_converters: {eligible_converters}')
            if len(eligible_converters) > 0:
                converter_id = eligible_converters[0]
            else:
                raise ValueError(f'No audio converter found for engine: {service_key}')
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'converter_id: {converter_id}')
            return converter_id
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        raise ValueError(f'Error occurred locating Transcoder for {service_key}')

    @classmethod
    def get_service_pipeline(cls, engine_id: str) -> List[StrEnum]:
        """
        Finds a player or transcoder/player combination that can play what is
        produced by the given engine.
        :param engine_id:
        :return:
        """
        pass


class AudioInformation:
    def __init__(self, service_id: ServiceID,
                 supports_cache: bool = True,
                 player_modes: List[PlayerMode] | None = None,
                 sound_capabilities: SoundCapabilities | None = None,
                 candidate_consumers: List[ServiceID] | None = None
                 ) -> None:
        self._service: ServiceID = service_id
        self._supports_cache: bool = supports_cache
        self._player_modes: List[PlayerMode] = player_modes
        self._sound_capabilities: List[SoundCapabilities] | None = sound_capabilities
        self._candidate_consumers: List[ServiceID] | None = candidate_consumers
        self._candidate_players: List[ServiceID] | None = None
        self._candidate_transcoders: List[ServiceID] | None = None

    def get_candidate_players(self) -> List[ServiceID]:
        if self._candidate_players is None:
            self._candidate_players = []
            for consumer in self._candidate_consumers:
                consumer: ServiceID

        return self._candidate_players
