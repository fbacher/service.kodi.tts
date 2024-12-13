# coding=utf-8
from __future__ import annotations  # For union operator |

import sys

from common.monitor import Monitor
from common.setting_constants import AudioType

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
from common.logger import BasicLogger

MY_LOGGER = BasicLogger.get_logger(__name__)


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
    _services_by_service_type: Dict[ServiceType, Dict[str, str]] = {}

    @classmethod
    def add_service(cls, service_id: StrEnum | str, service_types: List[ServiceType],
                    supported_input_formats: List[AudioType],
                    supported_output_formats: List[AudioType]) -> None:
        """
        :param service_types: services which this provides
        :param service_id: Uniquely identifies the engine, player or converter that
                these capabilities belong to
        :param supported_input_formats:
        :param supported_output_formats:
        """
        if isinstance(service_id, StrEnum):
            service_id = service_id.value
        for service_type in service_types:
            services_in_type: Dict[str, str]
            services_in_type = cls._services_by_service_type.get(service_type)
            if services_in_type is None:
                services_in_type = {}
                cls._services_by_service_type[service_type] = services_in_type
            services_in_type[service_id] = service_id

        if cls._capabilities_by_service.get(service_id) is None:
            cls._capabilities_by_service[service_id] = \
                (supported_input_formats, supported_output_formats)

    @classmethod
    def get_output_formats(cls, service_id: str) -> List[AudioType]:
        output_formats: List[AudioType]
        _, output_formats = cls._capabilities_by_service[service_id]
        return output_formats

    @classmethod
    def get_input_formats(cls, service_id: str) -> List[AudioType]:
        input_formats: List[AudioType]
        input_formats, _ = cls._capabilities_by_service[service_id]
        return input_formats

    @classmethod
    def get_capable_services(cls, service_type: ServiceType,
                             consumer_formats: List[AudioType] | AudioType,
                             producer_formats: List[AudioType] | AudioType)\
            -> List[str]:
        """
        TODO: Change to return ServiceType, List[service_id]
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
        if isinstance(producer_formats, str):
            producer_formats = [producer_formats]
        if isinstance(consumer_formats, str):
            consumer_formats = [consumer_formats]
        MY_LOGGER.debug(f'service_type: {service_type}')
        MY_LOGGER.debug(f'consumer_formats: {consumer_formats}')
        MY_LOGGER.debug(f'producer_formats: {producer_formats}')
        services_of_this_type: Dict[str, str]
        services_of_this_type = cls._services_by_service_type.get(service_type)
        if services_of_this_type is None:
            services_of_this_type = {}
        # Now, narrow down this list to the ones that can fulfill consumer/producer
        # requirements

        eligible_services: List[str] = []
        MY_LOGGER.debug(f'services_of_this_type: {services_of_this_type.keys()}')
        for service_id in services_of_this_type.keys():
            input_formats: List[AudioType]
            output_formats: List[AudioType]

            input_formats, output_formats = cls._capabilities_by_service[service_id]
            MY_LOGGER.debug(f'service_id: {service_id} input_formats: {input_formats}')
            MY_LOGGER.debug(f'output_formats: {output_formats}')
            supports_consumer: bool = False
            if len(consumer_formats) == 0:
                supports_consumer = True
            else:
                for audio_format in consumer_formats:
                    MY_LOGGER.debug(f'audio_format: {audio_format} type:'
                                    f' {type(audio_format)}')
                    if audio_format in input_formats:
                        supports_consumer = True
                        break
                    for input_format in input_formats:
                        if input_format == audio_format:
                            supports_consumer = True
                            break
                        MY_LOGGER.debug(f'input_format: {input_format} type:'
                                        f' {type(input_format)}')
                        MY_LOGGER.debug(f'audio_format: {audio_format} type:'
                                        f' {type(audio_format)}')

            supports_producer: bool = False
            if len(producer_formats) == 0:
                supports_producer = True
            else:
                for audio_format in producer_formats:
                    if audio_format in output_formats:
                        supports_producer = True
                        break
                    for output_format in output_formats:
                        MY_LOGGER.debug(f'output_format: {output_format} type:'
                                        f' {type(output_format)}')
                        MY_LOGGER.debug(f'audio_format: {audio_format} type:'
                                        f' {type(audio_format)}')
            if supports_consumer and supports_producer:
                eligible_services.append(service_id)

        return eligible_services

    @staticmethod
    def get_transcoder(service_id: str,
                       target_audio: AudioType = AudioType.MP3) -> str | None:
        """
        Finds a transcoder for the given service based upon its preference,
        availability and Transcoder preference

        :param service_id:
        :param target_audio: MP3 or WAVE
        :return: TransCoderType of found transcoder
                 or None if transcoder not neeeded
                 or ValueError if transcoder could not be found
        """
        Monitor.exception_on_abort(0.05)
        try:
            # converter_id: str = Settings.get_setting_str(SettingsProperties.TRANSCODER,
            #                                              service_id, ignore_cache=False,
            #                                              default=None)
            audio_types: List[AudioType]
            audio_types = SoundCapabilities.get_output_formats(service_id)
            MY_LOGGER.debug(f'{service_id} output_formats: {audio_types}')
            if target_audio in audio_types:
                return None  # No converter needed

            eligible_converters: List[str]
            eligible_converters = \
                SoundCapabilities.get_capable_services(ServiceType.TRANSCODER,
                                                       audio_types,
                                                       AudioType.MP3)
            MY_LOGGER.debug(f'eligible_converters: {eligible_converters}')
            if len(eligible_converters) > 0:
                converter_id = eligible_converters[0]
            else:
                raise ValueError(f'No audio converter found for engine: {service_id}')
            MY_LOGGER.debug(f'converter_id: {converter_id}')
            return converter_id
        except AbortException:
            reraise(*sys.exc_info())
        except Exception as e:
            MY_LOGGER.exception('')
        raise ValueError(f'Error occurred locating Transcoder for {service_id}')
