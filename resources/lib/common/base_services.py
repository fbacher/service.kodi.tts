# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.service_types import ServiceKey
from backends.settings.service_unavailable_exception import ServiceUnavailable

from backends.settings.service_types import ServiceID

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          IntValidator, NumericValidator,
                                          StringValidator)
from common.debug import Debug
from common.logger import BasicLogger
from common.phrases import Phrase, PhraseList
from common.settings import Settings

MY_LOGGER = BasicLogger.get_logger(__name__)


class IServices:
    """

    """
    service_id: ServiceID = None
    service_type: ServiceType = None
    service_key: ServiceID | None = None

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
        service_key: ServiceID = service.service_key
        key: str = service_key.service_key
        BaseServices.service_index[key] = service
        MY_LOGGER.debug(f'Registered {key} {type(key)} '
                        f'type: {type(service.service_id)} '
                        f'{repr(service)}')
        #  MY_LOGGER.debug(f'{BaseServices.service_index}')

    '''
    def register_settings(self, service: Type['BaseServices']) -> None:
        BaseServices.service_settings_index[service.setting_id] = service
        MY_LOGGER.debug(f'Registered Settings {service.setting_id} '
                        f'type: {type(service.setting_id)} '
                        f'{repr(service)}')
    '''

    #  @classmethod
    #  def getServiceTypes(cls, service_name: str) -> List[ServiceType]:
    #      sound_capabilities: SoundCapabilities = cls.getSoundCapabilities(service_name)
    #      if sound_capabilities is not None:
    #          return sound_capabilities.service_types

    @classmethod
    def get_service(cls, service_key: ServiceID) -> ForwardRef('BaseServices'):
        # MY_LOGGER.debug(f'service_key: {service_key} type: {type(service_key)}')
        key: str = service_key.service_key
        service: BaseServices | None
        service = BaseServices.service_index.get(key, None)

        if service is None:
            MY_LOGGER.info(f'Could not get service: {key} ')
            #  MY_LOGGER.info(f'services: {BaseServices.service_index}')
            active_service: bool = False
            raise ServiceUnavailable(service_key=service_key, reason=Status.UNKNOWN,
                                     active=active_service)
        if not SettingsMap.is_available(service_key):
            raise ServiceUnavailable(service_key,
                                     reason=Status.FAILED, active=None)
        return service

    @classmethod
    def get_available_service_ids(cls, service_type: ServiceType) -> List[ServiceID]:
        return SettingsMap.get_available_services(service_type)

    @classmethod
    def getValidator(cls, service_key: ServiceID,
                     setting_id: str) -> ConstraintsValidator:
        validator: ConstraintsValidator | IValidator
        validator = SettingsMap.get_validator(service_key=service_key)
        return validator

    '''
        'Global' SERVICES
    '''

    @classmethod
    def get_tts_version(cls) -> str:
        version_validator: StringValidator | IValidator
        version_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                             SettingProp.VERSION)
        return version_validator.get_tts_value()

    @classmethod
    def get_addons_md5(cls) -> str:
        addons_md5_val: StringValidator | IValidator
        addons_md5_val = cls.getValidator(ServiceKey.TTS_KEY,
                                          SettingProp.ADDONS_MD5)
        return addons_md5_val.get_tts_value()

    @classmethod
    def is_disable_broken_engines(cls) -> bool:
        disable_broken_engines_val: BoolValidator | IValidator
        disable_broken_engines_val = cls.getValidator(ServiceKey.TTS_KEY,
                                                      SettingProp.DISABLE_BROKEN_SERVICES)
        return disable_broken_engines_val.get_tts_value()

    @classmethod
    def is_speak_background_progress(cls) -> bool:
        speak_background_progress_validator: BoolValidator | IValidator
        speak_background_progress_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                                               SettingProp.SPEAK_BACKGROUND_PROGRESS)
        return speak_background_progress_validator.get_tts_value()

    @classmethod
    def is_speak_background_progress_during_media(cls) -> bool:
        speak_background_progress_during_media_validator: BoolValidator | IValidator
        speak_background_progress_during_media_validator = cls.getValidator(
            ServiceKey.TTS_KEY,
            SettingProp.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA)
        return speak_background_progress_during_media_validator.get_tts_value()

    @classmethod
    def uses_tempfs(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(ServiceKey.USE_TMPFS)
        return cache_validator.get_tts_value()

    """
    @classmethod
    def is_auto_item_extra(cls) -> bool:
        auto_item_extra_val: BoolValidator | IValidator
        auto_item_extra_val = cls.getValidator(ServiceKey.TTS_KEY,
                                               SettingProp.AUTO_ITEM_EXTRA)
        return auto_item_extra_val.get_tts_value()
    """

    @classmethod
    def is_speak_list_count(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                           SettingProp.SPEAK_LIST_COUNT)
        return cache_validator.get_tts_value()

    @classmethod
    def is_reader_on(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                           SettingProp.READER_ON)
        return cache_validator.get_tts_value()

    @classmethod
    def is_override_poll_interval(cls) -> bool:
        overide_poll_validator: BoolValidator | IValidator
        overide_poll_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                                  SettingProp.OVERRIDE_POLL_INTERVAL)
        return overide_poll_validator.get_tts_value()

    @classmethod
    def get_debug_log_level(cls) -> int:
        debug_log_level_validator: IntValidator | IValidator
        debug_log_level_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                                     SettingProp.DEBUG_LOG_LEVEL)
        return debug_log_level_validator.get_tts_value()

    @classmethod
    def get_poll_interval(cls) -> int:
        poll_interval_validator: IntValidator | IValidator
        poll_interval_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                                   SettingProp.POLL_INTERVAL)
        return poll_interval_validator.get_tts_value()

    @classmethod
    def get_cache_expiration_days(cls) -> int:
        expiration_validator: IntValidator | IValidator
        expiration_validator = cls.getValidator(ServiceKey.TTS_KEY,
                                                SettingProp.CACHE_EXPIRATION_DAYS)
        return expiration_validator.get_tts_value()

    @classmethod
    def get_background_progress_interval(cls) -> int:
        background_progress_interval_val: IntValidator | IValidator
        background_progress_interval_val = cls.getValidator(ServiceKey.TTS_KEY,
                                                            SettingProp.BACKGROUND_PROGRESS_INTERVAL)
        return background_progress_interval_val.get_tts_value()

    """
    @classmethod
    def get_auto_item_extra_delay(cls) -> int:
        extra_delay_val: IntValidator | IValidator
        extra_delay_val = cls.getValidator(ServiceKey.TTS_KEY,
                                           SettingProp.AUTO_ITEM_EXTRA_DELAY)
        return extra_delay_val.get_tts_value()
    """

    # @classmethod
    # def getSoundCapabilities(cls, service_name: str) -> SoundCapabilities:
    #     service: BaseServices = BaseServices.service_settings_index.get(service_name,
    #     None)
    #     if service is None:
    #         return None
    #     return service.sound_capabilities

    '''
        Applies to multiple services
    '''

    '''
    @classmethod
    def uses_pipe(cls, setting_id: str) -> bool:
        pipe_validator: BoolValidator | IValidator
        pipe_validator = cls.getValidator(setting_id, SettingProp.PIPE)
        return pipe_validator.get_tts_value()
    '''

    """
    Adapter code for SettingsMap. Can't have SettingsMap and BaseServices
    import each other
    """

    @classmethod
    def is_valid_property(cls, service_or_id: ServiceID,
                          property_id: str) -> bool:
        service_id: str
        if isinstance(service_or_id, str):
            service_id = service_or_id
        else:
            service_or_id: IServices
            service_id = service_or_id.service_id
        return SettingsMap.is_valid_setting(service_id, property_id)

    @classmethod
    def get_validator(cls, service_or_id: str,
                      property_id: str) -> IValidator | ConstraintsValidator | \
                                           StringValidator | IntValidator | \
                                           BoolValidator | NumericValidator | None:
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_id
        else:
            service_id = service_or_id
        return SettingsMap.get_validator(service_id)

    @classmethod
    def get_default_value(cls, service_or_id: str,
                          property_id: str) -> int | bool | str | float | None:
        settings_for_service: Dict[str, IValidator]
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_id
        else:
            service_id = service_or_id
        return SettingsMap.get_default_value(service_id, property_id)

    @classmethod
    def get_value(cls, service_or_id: str, property_id: str) \
            -> int | bool | float | str | None:
        settings_for_service: Dict[str, IValidator]
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_id
        else:
            service_id = service_or_id
        return SettingsMap.get_default_value(service_id, property_id)

    @classmethod
    def get_active_engine_id(cls) -> str:
        """
        Returns the id of the current engine
        :return:
        """
        return Settings.get_engine_id()

    @classmethod
    def get_alternate_engine_id(cls) -> str | None:
        """
        Returns the id of the engine to use in case the current/ctive
        engine is too slow to respond. This is typically used when the current
        engine is a remote service or is a slower, higher quality engine. The
        alternate engine should be a fast engine.

        Note that this is different from the default engine, which is used when
        the user preferred (current) engine is broken or otherwise unavailable.
        :return:
        """
        return Settings.get_alternate_engine_id()

    @classmethod
    def get_active_player_id(cls) -> str:
        # setting_id: str = cls.get_active_engine_id()
        # player_id: str = Settings.get_player_key(setting_id)
        # return player_id
        pass

    @classmethod
    def negotiate_engine_config(cls, engine_id: ServiceID, player_volume_adjustable: bool,
                                player_speed_adjustable: bool,
                                player_pitch_adjustable: bool) -> Tuple[bool, bool, bool]:
        """
        Player is informing engine what it is capable of controlling
        Engine replies what it is allowing player_key to control
        """
        pass


BaseServices.class_init()
