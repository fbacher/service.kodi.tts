# coding=utf-8

'''
    Helper to exchange audio related information between players, engines
    and anything else that can produce, consume or transform audio.
'''
from backends.settings.constraints import Constraints
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

    _all_service_capabilities: Dict[str, 'SoundCapabilities'] = {}

    def __init__(self, service_id: str, service_types: List[ServiceType],
                 supported_input_formats: List[str],
                 supported_output_formats: List[str],
                 available: bool = True) -> None:
        """
        :param service_types: services which this provides
        :param service_id: Uniquely identifies the engine, player or converter that
                these capabilities belong to
        :param supported_input_formats:
        :param supported_output_formats:
        :param available: when false, the service is unavailable, typically due
        to O/S incompatibility
        """
        self.service_types = service_types
        clz = type(self)
        clz._class_name = self.__class__.__name__
        if clz._logger is None:
            clz._logger = module_logger.getChild(clz._class_name)

        # supported formats such as: mp3, wav, etc.

        self.service_id = service_id
        self.supported_input_formats: List[str] = supported_input_formats
        self.supported_output_formats: List[str] = supported_output_formats
        self.supported_conversions: Dict[str, List[str]] = {}
        self.services_provided: Set[ServiceType] = set(service_types)
        self.available: bool = available
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

        SoundCapabilities._all_service_capabilities[service_id] = self

    def supportedOutputFormats(self) -> List[str]:
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
        return SoundCapabilities._all_service_capabilities.get(service_id, None)

    def get_candidate_consumers(self, service_type: ServiceType,
                                consumer_formats: List[str] | str,
                                producer_formats: List[str] | str) -> List[
        ForwardRef('SoundCapabilities')]:
        """
        Returns services which meet the given criteria.

        :param service_type: ex: engine, player, converter, etc.
               None means the service type will be ignored
        :param consumer_formats: audio formats that this service can consume
               An empty list means that the input audio format will be ignored
        :param producer_formats: audio formats that this service can produce
               An empty list means that the output audio format will be ignored
        :return:

        Note that the producer_formats field will usually be empty.

        The order is determined by 1) the order of preferred producer formats by
        this service and 2) the order of preferred consumer formats by the consumers.
        """
        clz = type(self)
        candidate_consumers: List[ForwardRef('SoundCapabilities')] = []
        if service_type is None:
            service_type = ServiceType.ALL
        if consumer_formats is None:
            consumer_formats = []
        if not isinstance(consumer_formats, List):
            tmp: str = consumer_formats
            consumer_formats: List[str] = [tmp]
        if producer_formats is None:
            producer_formats = []
        if not isinstance(producer_formats, List):
            tmp: str = producer_formats
            producer_formats = [tmp]

        producer_formats.extend(self.supported_output_formats)
        produces: Dict[str, None] = {}

        # Turn into an ordered set
        for producer_format in producer_formats:
            produces[producer_format] = None

        for producer_format in produces.keys():
            producer_format: str
            for service_capabilities in SoundCapabilities._all_service_capabilities.values():
                service_capabilities: 'SoundCapabilities'
                if (((service_type == ServiceType.ALL)
                     or (service_type in service_capabilities.services_provided))
                        and service_capabilities.is_supports_input_format(producer_format)
                        and service_capabilities.available):
                    candidate_consumers.append(service_capabilities)

        return candidate_consumers
