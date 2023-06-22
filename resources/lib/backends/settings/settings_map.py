# coding=utf-8
from backends.settings.i_validators import (IBoolValidator, IIntValidator,
                                            IStrEnumValidator, IValidator,
                                            IStringValidator)
from common.logger import BasicLogger
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class SettingsMap:
    """
    A map of all possible settings and their type.

    This is needed since we have our own settings GUI and don't rely on
    settings.xml having every setting name and type info (can't easily access it
    anyway), we instead depend on this map as well as validators, constraints, etc.

    The setting names are nearly the same between the different engines, etc., but
    not identical. The Settings class creates default values, but in order to do this
    it needs to reliably know: 1) all of the properties, 2) at least all of the
    default values. Better yet, if it knows 3) which values are valid.

    Settings are kept in a two-level map. The first level maps the service_id to
    a secondary map of that service's settings.
    """

    # Maps a service ('eSpeak') to map of it's settings.
    # Service and setting ids are defined in settings_constants.
    #
    # These maps are built by the services themselves. The are defined at startup.
    # Note that only settings of type string, integer and boolean are defined,
    # more can be added, as needed. More complex types such as float and lists of
    # the basic types are supported by Kodi, but since it complicates users from
    # reading settings.xml, those types are avoided. Floats are emulated by
    # storing values as integers, but scaling them as needed for UI presentation

    service_to_settings_map: Dict[str, Dict[str, IValidator]] = {}

    _initialized: bool = False
    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        if clz._initialized:
            return
        clz._initialized = True
        clz._logger = module_logger.getChild(clz.__name__)

    @classmethod
    def define_setting(cls, service_id: str, property_id: str, validator: IValidator):
        """
        Defines a validator to use for a given property of a service
        :param service_id: Specifies the service: 'engine', 'player', etc. When
        the property has no service, then the service is 'tts'
        :param property_id: Specifies the property: volume, cache-path, etc.
        :param validator:
        """
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        cls._logger.info(f'service: {service_id}.{property_id} '
                         f'cls: {cls.__name__}')
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            settings_for_service = {}
            cls.service_to_settings_map[service_id] = settings_for_service
        #
        # Allow to override any previous entry since doing otherwise would complicate
        # initialization order since it is normal to initialize your ancestor
        # prior to yourself

        settings_for_service[property_id] = validator

    @classmethod
    def is_valid_property(cls, service_id: str, property_id: str) -> bool:
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            return False

        if property_id not in settings_for_service:
            return False
        return True

    @classmethod
    def get_validator(cls, service_id: str,
                      property_id: str) -> IBoolValidator | IStringValidator | \
                                           IIntValidator | IStrEnumValidator | None:
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            return None
        return settings_for_service.get(property_id)


    @classmethod
    def get_default_value(cls, service_id: str,
                          property_id: str) -> int | bool | str | float | None:
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        validator: IValidator = cls.get_validator(service_id, property_id)
        if validator is None:
            return None
        return validator.default_value

    @classmethod
    def get_allowed_values(cls, service_id: str,
                          property_id: str) -> List[str] | None:
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        validator: IValidator = cls.get_validator(service_id, property_id)
        if validator is None:
            return None
        if not isinstance(validator, IStringValidator):
            return None
        validator: IStringValidator
        return validator.allowed_values

    @classmethod
    def get_value(cls, service_id: str, property_id: str) \
            -> int | bool | float | str | None:
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        validator: IValidator = cls.get_validator(service_id, property_id)
        if validator is None:
            return None
        return validator.getValue()

SettingsMap()
