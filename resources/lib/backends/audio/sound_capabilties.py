# coding=utf-8

'''
    Helper to exchange audio related information between players, engines
    and anything else that can produce, consume or transform audio.
'''
from backends.settings.service_types import ServiceType
from common.logger import BasicLogger
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SoundCapabilities:
    """
        Helper class to exchange audio related information between players, engines
        and anything else that can produce, consume or transform audio.
    """
    _logger: BasicLogger = None

    WAVE: str = '.wav'
    MP3: str = '.mp3'

    # Sound capabilities are used by engines (which only produce), players
    # (which can play or sometimes convert and play) or converters, which
    # perform some manipulation of the audio and pass it on to it's consumer
    # _all_service_capabilites keeps a map of the capabilities of all services

    _capabilities_by_service: Dict[str, Tuple[List[str], List[str]]] = {}
    _services_by_service_type: Dict[ServiceType, List[str]] = {}

    def __init__(self):
        cls = type(self)
        cls._class_name = self.__class__.__name__
        if cls._logger is None:
            cls._logger = module_logger.getChild(cls._class_name)

    @classmethod
    def add_service(cls, service_id: str, service_types: List[ServiceType],
                 supported_input_formats: List[str],
                 supported_output_formats: List[str]) -> None:
        """
        :param service_types: services which this provides
        :param service_id: Uniquely identifies the engine, player or converter that
                these capabilities belong to
        :param supported_input_formats:
        :param supported_output_formats:
        """

        # service_type can be 'engine' or 'player' or 'converter' Frequently
        # a player can also be a converter.
        # So, mplayer can be a player or converter service type
        for service_type in service_types:
            services_in_type: List[str]
            services_in_type = cls._services_by_service_type.get(service_type)
            if services_in_type is None:
                services_in_type = []
                cls._services_by_service_type[service_type] = services_in_type
            services_in_type.append(service_id)

        if cls._capabilities_by_service.get(service_id) is None:
            cls._capabilities_by_service[service_id] = \
                (supported_input_formats, supported_output_formats)

    @classmethod
    def get_output_formats(cls, service_id: str) -> List[str]:
        output_formats: List[str]
        _, output_formats = cls._capabilities_by_service[service_id]
        return output_formats

    @classmethod
    def get_input_formats(cls, service_id: str) -> List[str]:
        input_formats: List[str]
        input_formats, _ = cls._capabilities_by_service[service_id]
        return input_formats

    @classmethod
    def get_capable_services(cls, service_type: ServiceType,
                             consumer_formats: List[str] | str,
                             producer_formats: List[str] | str) -> List[str]:
        """
        Returns services which meet the given criteria.

        :param service_type: ex: engine, player, converter, etc.
               None means the service type will be ignored
        :param consumer_formats: audio formats that this service must consume from
               the previous service
               An empty list means that the output audio format will be ignored
        :param producer_formats: preferred/required formats that the current service
               should produce. An empty list means that there are no restrictions
        :return:

        Note that the producer_formats field will usually be empty.

        The order is determined by 1) the order of preferred producer formats by
        this service and 2) the order of desired formats produced by this stage.
        """

        """
        A chain of tools is required to voice text:
        examples: engine -> wav -> player
                  engine -> wav -> converter -> .mp3 -> cache -> player
                  cache -> mp3 -> player
                    
        The job of this module is to determine the candidate tools for the next stage
        in a sequence. For example, if we are at the engine stage that produces wave
        and we next need to play the sound, then we need a player that can play wave,
        or a converter to mp3 then a player.
        
        The major determinant is whether caching is used or not. If caching is used, 
        then mp3 is required (much smaller files). Otherwise, may as well do everything
        in wave since it requires less cpu.
        """
        services_of_this_type: List[str] = cls._services_by_service_type.get(service_type)
        if services_of_this_type is None:
            services_of_this_type = []
        # Now, narrow down this list to the ones that can fulfill consumer/producer
        # requirements

        eligible_services: List[str] = []
        for service_id in services_of_this_type:
            input_formats: List[str]
            output_formats: List[str]

            input_formats, output_formats = cls._capabilities_by_service[service_id]
            supports_consumer: bool = False
            if len(consumer_formats) == 0:
                supports_consumer = True
            else:
                for format in consumer_formats:
                    if format in input_formats:
                        supports_consumer = True
                        break

            supports_producer: bool = False
            if len(producer_formats) == 0:
                supports_producer = True
            else:
                for format in producer_formats:
                    if format in output_formats:
                        supports_producer = True
            if supports_consumer and supports_producer:
                eligible_services.append(service_id)

        return eligible_services
