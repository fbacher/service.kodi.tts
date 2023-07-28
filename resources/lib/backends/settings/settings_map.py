# coding=utf-8
from strenum import StrEnum

from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import (IBoolValidator, IConstraintsValidator,
                                            IIntValidator,
                                            IStrEnumValidator, IValidator,
                                            IStringValidator)
from backends.settings.service_types import ServiceType
from common.logger import BasicLogger
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Reason(StrEnum):
    """

    """
    UNKNOWN = 'unknown'
    AVAILABLE = 'available'
    NOT_AVAILABLE = 'not_available'
    BROKEN = 'broken'


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
    service_availability_map: Dict[str, Reason] = {}

    service_to_properties_map: Dict[str, Dict[str, Any]] = {}

    # Index to get all of the service_ids for a particular ServiceType.
    # Example: ServiceType.ENGINE, ServiceType.PLAYER, etc.
    #
    service_type_to_services_map: Dict[ServiceType, Dict[str, Dict[str, Any]]] = {}

    _initialized: bool = False
    _logger: BasicLogger = None

    def __init__(self):
        clz = type(self)
        if clz._initialized:
            return
        clz._initialized = True
        clz._logger = module_logger.getChild(clz.__name__)

    @classmethod
    def define_service(cls, service_type: ServiceType, service_id: str,
                       service_properties: Dict[str, Any]):
        try:
            props_for_service: Dict[str, Dict[str, Any]] | None
            props_for_service = cls.service_type_to_services_map.get(service_type)
            if props_for_service is None:
                props_for_service = {}
                cls.service_type_to_services_map[service_type] = props_for_service
            props_for_service[service_id] = service_properties
            cls.service_to_properties_map[service_id] = service_properties
        except Exception as e:
            cls._logger.exception('')

    @classmethod
    def get_services_for_service_type(cls, service_type: ServiceType) \
                                        -> List[Tuple[str, str]]:
        services: List[Tuple[str, str]] = []
        service_dict: Dict[str, Any] = cls.service_type_to_services_map.get(service_type,
                                                                            {})
        for service_id, name_dict in service_dict.items():
            name: str = name_dict['name']
            services.append((service_id, name))

        return services

    @classmethod
    def get_service_properties(cls, service_id: str) -> Dict[str, Any]:
        service_props: Dict[str, Any]
        service_props = cls.service_to_properties_map.get(service_id)
        if service_props is None:
            service_props = {}
        return service_props

    @classmethod
    def get_service_property(cls, service_id: str, property: str) -> Any:
        properties: Dict[str, Any] = cls.get_service_properties(service_id)
        return properties.get(property, None)

    @classmethod
    def get_available_service_ids(cls, service_type) -> List[Tuple[str, Dict[str, Any]]] | None:
        if not ServiceType.ALL.value <= service_type.value <= \
               ServiceType.LAST_SERVICE_TYPE.value:
            cls._logger.debug(f'Invalid ServiceType: {service_type}')
            return None

        service_ids: Dict[str, str] = cls.get_service_properties(service_type)
        available_service_ids: List[Tuple[str, Dict[str, Any]]] = []
        service_id: str
        properties: Dict[str, Any]
        for service_id, properties in service_ids.items():
            if cls.service_availability_map.get(service_id, Reason.UNKNOWN) == Reason.AVAILABLE:
                available_service_ids.append((service_id, properties))
        return available_service_ids

    @classmethod
    def set_is_available(cls, service_id: str, reason: Reason) -> None:
        cls.service_availability_map[service_id] = reason

    @classmethod
    def is_available(cls, service_id) -> Tuple[bool, Reason]:
        reason: Reason = cls.service_availability_map.get(service_id, None)
        if reason is None:
            cls.set_is_available(service_id, Reason.UNKNOWN)
            return False, Reason.UNKNOWN

        if reason == Reason.AVAILABLE:
            return True, reason
        return False, reason


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

        if property_id not in settings_for_service.keys():
            return False
        return True

    @classmethod
    def get_validator(cls, service_id: str,
                      property_id: str) -> IBoolValidator | IStringValidator | \
                                           IIntValidator | IStrEnumValidator | \
                                           IConstraintsValidator | None:
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
    def get_constraints(cls, service_id: str, property_id: str) -> IConstraints:
        validator: IConstraintsValidator
        validator = cls.get_validator(service_id, property_id)
        constraints: IConstraints
        constraints = validator.constraints
        return constraints

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
        return validator.get_allowed_values()

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
        value = validator.get_tts_value()
        return value


SettingsMap()
