from backends.players.iplayer import IPlayer
from backends.settings.i_validators import IValidator
from backends.settings.service_types import Services, ServiceType
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import (BoolValidator, ConstraintsValidator,
                                          IntValidator, StringValidator)
from common.logger import BasicLogger
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class IServices:
    """

    """
    service_ID: str = None
    service_TYPE: ServiceType = None
    #  sound_capabilities: SoundCapabilities = None


class BaseServices(IServices):
    """
    """

    # Two level index. First index by the service_ID, then by service_Type which then
    service_index: Dict[str, Type['BaseServices']] = {}
    service_settings_index: Dict[str, Type['BaseServices']] = {}
    #  sound_capabilities: SoundCapabilities = None
    _logger: BasicLogger = None

    def __init__(self, *args, **kwargs):
        clz = type(self)
        BaseServices._logger = module_logger.getChild(clz.__name__)

    @classmethod
    def register(cls, service: Type['BaseServices']) -> None:
        BaseServices.service_index[service.service_ID] = service
        BaseServices._logger.debug(f'Registering {repr(service)}')

    def register_settings(self, service: Type['BaseServices']) -> None:
        BaseServices.service_settings_index[service.service_ID] = service

    #  @classmethod
    #  def getServiceTypes(cls, service_name: str) -> List[ServiceType]:
    #      sound_capabilities: SoundCapabilities = cls.getSoundCapabilities(service_name)
    #      if sound_capabilities is not None:
    #          return sound_capabilities.service_types

    @classmethod
    def getService(cls, service_name: str) -> ForwardRef('BaseServices'):
        service: BaseServices | None = BaseServices.service_index.get(service_name, None)
        return service

    @classmethod
    def getValidator(cls, service_id: str, setting_id: str) -> ConstraintsValidator:
        validator: ConstraintsValidator | IValidator
        validator = SettingsMap.get_validator(service_id=service_id,
                                              property_id=setting_id)
        return validator

    '''
        'Global' SERVICES
    '''

    @classmethod
    def get_cache_path(cls) -> str:
        cache_path_validator: StringValidator | IValidator
        cache_path_validator = cls.getValidator(Services.TTS_SERVICE,
                                                SettingsProperties.CACHE_PATH)
        return cache_path_validator.getValue()

    @classmethod
    def get_tts_version(cls) -> str:
        version_validator: StringValidator | IValidator
        version_validator = cls.getValidator(Services.TTS_SERVICE,
                                             SettingsProperties.VERSION)
        return version_validator.getValue()

    @classmethod
    def get_addons_md5(cls) -> str:
        addons_md5_val: StringValidator | IValidator
        addons_md5_val = cls.getValidator(Services.TTS_SERVICE,
                                          SettingsProperties.ADDONS_MD5)
        return addons_md5_val.getValue()

    @classmethod
    def uses_cache(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.CACHE_SPEECH)
        return cache_validator.getValue()

    @classmethod
    def is_disable_broken_engines(cls) -> bool:
        disable_broken_engines_val: BoolValidator | IValidator
        disable_broken_engines_val = cls.getValidator(Services.TTS_SERVICE,
                                                      SettingsProperties.DISABLE_BROKEN_SERVICES)
        return disable_broken_engines_val.getValue()

    @classmethod
    def is_speak_background_progress(cls) -> bool:
        speak_background_progress_validator: BoolValidator | IValidator
        speak_background_progress_validator = cls.getValidator(Services.TTS_SERVICE,
                                                               SettingsProperties.SPEAK_BACKGROUND_PROGRESS)
        return speak_background_progress_validator.getValue()

    @classmethod
    def is_speak_background_progress_during_media(cls) -> bool:
        speak_background_progress_during_media_validator: BoolValidator | IValidator
        speak_background_progress_during_media_validator = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.SPEAK_BACKGROUND_PROGRESS_DURING_MEDIA)
        return speak_background_progress_during_media_validator.getValue()

    @classmethod
    def uses_tempfs(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.USE_TEMPFS)
        return cache_validator.getValue()

    @classmethod
    def is_auto_item_extra(cls) -> bool:
        auto_item_extra_val: BoolValidator | IValidator
        auto_item_extra_val = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.AUTO_ITEM_EXTRA)
        return auto_item_extra_val.getValue()

    @classmethod
    def is_speak_list_count(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.SPEAK_LIST_COUNT)
        return cache_validator.getValue()

    @classmethod
    def is_reader_on(cls) -> bool:
        cache_validator: BoolValidator | IValidator
        cache_validator = cls.getValidator(Services.TTS_SERVICE, SettingsProperties.READER_ON)
        return cache_validator.getValue()

    @classmethod
    def is_override_poll_interval(cls) -> bool:
        overide_poll_validator: BoolValidator | IValidator
        overide_poll_validator = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.OVERRIDE_POLL_INTERVAL)
        return overide_poll_validator.getValue()

    @classmethod
    def get_debug_log_level(cls) -> int:
        debug_log_level_validator: IntValidator | IValidator
        debug_log_level_validator = cls.getValidator(Services.TTS_SERVICE,
                                                     SettingsProperties.DEBUG_LOG_LEVEL)
        return debug_log_level_validator.getValue()

    @classmethod
    def get_poll_interval(cls) -> int:
        poll_interval_validator: IntValidator | IValidator
        poll_interval_validator = cls.getValidator(Services.TTS_SERVICE,
                                                   SettingsProperties.POLL_INTERVAL)
        return poll_interval_validator.getValue()

    @classmethod
    def get_cache_expiration_days(cls) -> int:
        expiration_validator: IntValidator | IValidator
        expiration_validator = cls.getValidator(Services.TTS_SERVICE,
                                                SettingsProperties.CACHE_EXPIRATION_DAYS)
        return expiration_validator.getValue()

    @classmethod
    def get_background_progress_interval(cls) -> int:
        background_progress_interval_val: IntValidator | IValidator
        background_progress_interval_val = cls.getValidator(Services.TTS_SERVICE,
                                                SettingsProperties.BACKGROUND_PROGRESS_INTERVAL)
        return background_progress_interval_val.getValue()

    @classmethod
    def get_auto_item_extra_delay(cls) -> int:
        extra_delay_val: IntValidator | IValidator
        extra_delay_val = cls.getValidator(Services.TTS_SERVICE,
                                           SettingsProperties.AUTO_ITEM_EXTRA_DELAY)
        return extra_delay_val.getValue()

    # @classmethod
    # def getSoundCapabilities(cls, service_name: str) -> SoundCapabilities:
    #     service: BaseServices = BaseServices.service_settings_index.get(service_name, None)
    #     if service is None:
    #         return None
    #     return service.sound_capabilities

    '''
        Applies to multiple services
    '''
    @classmethod
    def uses_pipe(cls, service_id: str) -> bool:
        pipe_validator: BoolValidator | IValidator
        pipe_validator = cls.getValidator(service_id, SettingsProperties.PIPE)
        return pipe_validator.getValue()

    """
    Adapter code for SettingsMap. Can't have SettingsMap and BaseServices
    import each other
    """

    @classmethod
    def is_valid_property(cls, service_or_id: str,
                          property_id: str) -> bool:
        service_id: str
        if isinstance(service_or_id, str):
            service_id = service_or_id
        else:
            service_or_id: IServices
            service_id = service_or_id.service_ID
        return SettingsMap.is_valid_property(service_id, property_id)

    @classmethod
    def get_validator(cls, service_or_id: str,
                      property_id: str) -> IValidator | ConstraintsValidator | \
                                           StringValidator | IntValidator | \
                                           BoolValidator | None:
        settings_for_service: Dict[str, IValidator]
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_ID
        else:
            service_id = service_or_id
        return SettingsMap.get_validator(service_id, property_id)

    @classmethod
    def get_default_value(cls, service_or_id: str,
                          property_id: str) -> int | bool | str | float | None:
        settings_for_service: Dict[str, IValidator]
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_ID
        else:
            service_id = service_or_id
        return SettingsMap.get_default_value(service_id, property_id)

    @classmethod
    def get_value(cls, service_or_id: str, property_id: str) \
            -> int | bool | float | str | None:
        settings_for_service: Dict[str, IValidator]
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_ID
        else:
            service_id = service_or_id
        return SettingsMap.get_default_value(service_id, property_id)

    @classmethod
    def get_player_id(cls, service_or_id: str, property_id: str) \
            -> int | bool | float | str | None:
        service_id: str
        if isinstance(service_or_id, BaseServices):
            service_id = service_or_id.service_ID
        else:
            service_id = service_or_id
        validator: IValidator = cls.get_validator(service_id, property_id)
        if validator is None:
            return None
        return validator.getValue()
