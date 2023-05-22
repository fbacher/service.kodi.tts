# coding=utf-8

'''
    Helper to exchange audio related information between players, engines
    and anything else that can produce, consume or transform audio.
'''
from enum import Enum

from backends.constraints import Constraints
from common.logger import BasicLogger
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ServiceType(Enum):
    """
        Indicates which services are provided
    """
    ALL = 0
    # Produces Audio
    ENGINE = 1
    # Services are external to Kodi (ex. Speech Dispatcher)
    EXTERNAL_SERVICE = 2
    # Provides caching service
    CACHE_READER = 3
    CACHE_WRITER = 4
    # Converts audio formats
    CONVERTER = 5
    # Provides PIPE for services that can't
    PIPE_ADAPTER = 6
    # Plays Audio
    PLAYER = 7


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

    _all_service_capabilities: Dict[str, 'SoundCapabilities'] = {}

    def __init__(self, service_id: str, services: List[ServiceType],
                 supported_input_formats: List[str],
                 supported_output_formats: List[str]) -> None:
        '''

        :param service_id: Uniquely identifies the engine, player or converter that
                these capabilities belong to
        :param supported_input_formats:
        :param supported_output_formats:
        '''
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)

        # supported formats such as: mp3, wav, etc.

        self.supported_input_formats: List[str] = supported_input_formats
        self.supported_output_formats: List[str] = supported_output_formats
        self.supported_conversions: Dict[str, List[str]] = {}
        self.services_provided: Set[ServiceType] = set(services)
        self.can_change_speed: bool = False
        self.can_preserve_pitch: bool = False
        self.can_change_pitch: bool = False
        self.can_change_volume: bool = False
        self.volume_constraints: Constraints = None
        self.speed_constraints: Constraints = None
        self.pitch_constraints: Constraints = None
        self.can_receive_pipe: bool = False
        self.can_send_pipe: bool = False

        # Can this service persist across multiple voicings?
        # (typically to improve performance)

        self.can_act_as_server: bool = False
        self.can_recieve_sound_bytes: bool = False
        self.can_send_sound_bytes: bool = False
        self.can_receive_sound_file: bool = False
        self.can_send_sound_file: bool = False
        self.backup_engine_desired: bool = False

        clz._all_service_capabilities[service_id] = self

    def supportedOutFormats(self) -> List[str]:
        return self.supported_output_formats

    def supportedInputFormats(self) -> List[str]:
        return self.supported_input_formats

    def is_supports_input_format(self, audio_format: str) -> bool:
        return audio_format in self.supported_input_formats

    def is_supports_output_format(self, audio_format: str) -> bool:
        return audio_format in self.supported_output_formats

    def can_convert_format(self, from_format: str, to_format: str) -> bool:
        converts_to: List[str] | None = self.supported_conversions.get(from_format, None)
        return to_format in converts_to

    @classmethod
    def get_by_service_id(cls, service_id: str):
        return cls._all_service_capabilities.get(service_id, None)

    def get_candidate_consumers(self, service_type: ServiceType,
                                preferred_producer_format: str,
                                preferred_consumer_format: str) -> List[ForwardRef('SoundCapabilities')]:
        """
        Collects every service, such as pipe, converter, cache, agent or player
        that can consume one of the formats that this service can produce.
        The order is determined by 1) the order of preferred producer formats by
        this service and 2) the order of preferred consumer formats by the consumers.

        Other criteria will ultimately decide what is chosen.

        :param service_type:
        :param preferred_producer_format:
        :param preferred_consumer_format:
        :return:
        """
        clz = type(self)
        candidate_consumers: List[ForwardRef('SoundCapabilities')] = []
        producer_formats: List[str] = []
        if preferred_producer_format is not None:
            producer_formats.append(preferred_producer_format)
        producer_formats.extend(self.supported_output_formats)
        for producer_format in producer_formats:
            producer_format: str
            for service_capabilities in clz._all_service_capabilities:
                service_capabilities: 'SoundCapabilities'
                if (((service_type == ServiceType.ALL)
                    or (service_capabilities.service_type == service_type))
                    and service_capabilities.is_supports_input_format(producer_format)):
                    candidate_consumers.append(service_capabilities)
        return candidate_consumers
