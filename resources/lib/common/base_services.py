# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.service_unavailable_exception import ServiceUnavailable

from backends.settings.service_types import ServiceID
from cache.voicecache import VoiceCache
from common.monitor import Monitor

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.service_types import Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from common.logger import *
from common.phrases import Phrase, PhraseList

MY_LOGGER = BasicLogger.get_logger(__name__)


class IServices:
    """

    """
    service_id: ServiceID = None
    service_type: ServiceType = None
    service_key: ServiceID | None = None
    _shutdown: bool = False

    #  sound_capabilities: SoundCapabilities = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Few engines implement

    def seed_text_cache(self, phrases: PhraseList) -> None:
        raise NotImplementedError()

    def getVolumeDb(self) -> float:
        raise NotImplementedError()

    def getVolume(self) -> float:
        raise NotImplementedError()

    def say_phrase(self, phrase: Phrase) -> None:
        raise NotImplementedError()


class BaseServices(IServices):
    """
    """

    # service_index keeps a reference to every usable service from startup. The
    # index is <service_type>.<service_id> or ServiceID.service_key
    # See the get_service method.
    service_index: Dict[str, Type['BaseServices']] = {}

    # service_settings_index: Dict[str, Type['BaseServices']] = {}
    #  sound_capabilities: SoundCapabilities = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        super(BaseServices, self).__init__(*args, **kwargs)
        Monitor.register_abort_listener(clz.onAbortRequested, name='BSvcs')

    @classmethod
    def onAbortRequested(cls):
        cls._shutdown = True
        cls.service_index.clear()


    @classmethod
    def class_init(cls):
        pass

    @classmethod
    def register(cls,
                 service: Union[IServices, ForwardRef('BaseServices')]) -> None:
        """
        Registers this service so that the class instance can be retrived by
        BaseServices.get_service(ServiceID(ServiceType, service_name)), which
        is the same as BaseServices.get_service(<service_class>.service_key)
        :param service:
        :return:
        """
        if cls._shutdown:
            return

        service_key: ServiceID = service.service_key
        key: str = service_key.service_key
        BaseServices.service_index[key] = service
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Registered {key} {type(key)} '
                            f'type: {type(service.service_id)} '
                            f'{repr(service)}')
        #  MY_LOGGER.debug(f'{BaseServices.service_index}')

    #  @classmethod
    #  def getServiceTypes(cls, service_name: str) -> List[ServiceType]:
    #      sound_capabilities: SoundCapabilities = cls.getSoundCapabilities(service_name)
    #      if sound_capabilities is not None:
    #          return sound_capabilities.service_types

    @classmethod
    def get_service(cls, service_key: ServiceID) -> ForwardRef('BaseServices'):
        if cls._shutdown:
            return None

        MY_LOGGER.debug(f'service_key: {service_key} type: {type(service_key)}')
        MY_LOGGER.debug(f'key: {service_key.service_key}')

        service: BaseServices | None = None
        if service_key is None:
            raise ServiceUnavailable(service_key=None, reason=Status.UNKNOWN,
                                     active=False)
        key: str = service_key.service_key
        service = BaseServices.service_index.get(key, None)

        if service is None:
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug_v(f'Could not get service: {key} ')
            active_service: bool = False
            raise ServiceUnavailable(service_key=service_key, reason=Status.UNKNOWN,
                                     active=active_service)
        if not SettingsMap.is_available(service_key):
            raise ServiceUnavailable(service_key,
                                     reason=Status.FAILED, active=None)
        MY_LOGGER.debug(f'service: type: {type(service)}')
        return service

    @classmethod
    def get_available_service_ids(cls, service_type: ServiceType) -> List[ServiceID]:
        if cls._shutdown:
            return []

        return SettingsMap.get_available_services(service_type)

    def get_voice_cache(self) -> VoiceCache:
        raise NotImplementedError


BaseServices.class_init()
