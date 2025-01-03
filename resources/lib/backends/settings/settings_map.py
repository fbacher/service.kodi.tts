# coding=utf-8
from __future__ import annotations  # For union operator |

from pathlib import Path
from enum import Enum

from backends.settings.setting_properties import SettingsProperties

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import (AllowedValue, IBoolValidator,
                                            IChannelValidator,
                                            IConstraintsValidator,
                                            IGenderValidator, IIntValidator,
                                            INumericValidator, IStrEnumValidator,
                                            IStringValidator, IValidator)
from backends.settings.service_types import ServiceType
from common.logger import BasicLogger, DEBUG_V

MY_LOGGER = BasicLogger.get_logger(__name__)


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
    # These maps are built by the services themselves. They are defined at startup.
    # Note that only settings of type string, integer and boolean are defined,
    # more can be added, as needed. More complex types such as float and lists of
    # the basic types are supported by Kodi, but since it complicates users from
    # reading settings.xml, those types are avoided. Floats are emulated by
    # storing values as integers, but scaling them as needed for UI presentation

    service_to_settings_map: Dict[str, Dict[str, IValidator]] = {}
    service_availability_map: Dict[str, Reason] = {}

    service_to_properties_map: Dict[str, Dict[str, Any]] = {}

    # Index to get all the service_ids for a particular ServiceType.
    # Example: ServiceType.ENGINE, ServiceType.PLAYER, etc.
    #
    service_type_to_services_map: Dict[ServiceType, Dict[str, Dict[str, Any]]] = {}

    @classmethod
    def define_service(cls, service_type: ServiceType, service_id: str,
                       service_properties: Dict[str, Any]):
        """
        Defines a service (ex. google engine) and a property-value map for it.
        The map defines properties that the service itself has. It does NOT
        specify what settings the service has (ex. an engine's player is NOT
        a property of the service, it is a setting). Examples of service_properties
        include the displayName of the service, maxium phrase length and the
        cache suffix.

        :param service_type: ServiceType.ENGINE, player, etc
        :param service_id: engine-id, player-id, etc.
        :param service_properties:
        :return:
        """
        try:
            props_for_service: Dict[str, Dict[str, Any]] | None
            props_for_service = cls.service_type_to_services_map.get(service_type)
            if props_for_service is None:
                props_for_service = {}
                cls.service_type_to_services_map[service_type] = props_for_service
            props_for_service[service_id] = service_properties
            cls.service_to_properties_map[service_id] = service_properties
        except Exception as e:
            MY_LOGGER.exception('')

    @classmethod
    def get_services_for_service_type(cls, service_type: ServiceType) \
            -> List[Tuple[str, str]]:
        """
          Returns a list of services that have registered via
          SettingsMap.define_service(ServiceType.xxx, serviceID, properties)

          Useful for finding all of the engines that work with TTS, etc.
        :param service_type:
        :return: A Tuple [service_id, name] Where name is the value of
                 any property named 'name' when this was defined, or
                 with name having a message indicating the name was not specified.
        """
        services: List[Tuple[str, str]] = []
        service_dict: Dict[str, Any] = cls.service_type_to_services_map.get(service_type,
                                                                            {})
        for service_id, name_dict in service_dict.items():
            name: str = name_dict.get('name')
            if name is None:
                name = 'No name given'
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
    def get_service_property(cls, service_id: str, property: str | Path) -> Any:
        properties: Dict[str, Any] = cls.get_service_properties(service_id)
        return properties.get(property, None)

    @classmethod
    def get_available_service_ids(cls, service_type) -> List[Tuple[
        str, Dict[str, Any]]] | None:
        if not ServiceType.ALL.value <= service_type.value <= \
               ServiceType.LAST_SERVICE_TYPE.value:
            MY_LOGGER.debug(f'Invalid ServiceType: {service_type}')
            return None

        service_ids: Dict[str, str] = cls.get_service_properties(service_type)
        available_service_ids: List[Tuple[str, Dict[str, Any]]] = []
        service_id: str
        properties: Dict[str, Any]
        for service_id, properties in service_ids.items():
            if cls.service_availability_map.get(service_id,
                                                Reason.UNKNOWN) == Reason.AVAILABLE:
                available_service_ids.append((service_id, properties))
        return available_service_ids

    @classmethod
    def set_is_available(cls, service_id: str, reason: Reason) -> None:
        if reason != Reason.AVAILABLE:
            MY_LOGGER.debug(f'{service_id} is available reason: {reason}')
        else:
            MY_LOGGER.debug(f'{service_id} is available')
        cls.service_availability_map[service_id] = reason

    @classmethod
    def is_available(cls, service_id) -> bool:
        reason: Reason = cls.service_availability_map.get(service_id, None)
        if reason is None:
            return True
            # MY_LOGGER.debug(f'{service_id} availability UNKNOWN')
            # cls.set_is_available(service_id, Reason.UNKNOWN)
            # return False

        if reason == Reason.AVAILABLE:
            return True
        return False

    @classmethod
    def define_setting(cls, service_id: str, property_id: str,
                       validator: IValidator | None):
        """
        Defines a validator to use for a given property of a service
        :param service_id: Specifies the service: 'engine', 'player', etc. When
        the property has no service, then the service is 'tts'
        :param property_id: Specifies the property: volume, cache-path, etc.
        :param validator: If None, then the setting is NOT supported and any
                          prior definition is removed.
        """
        # MY_LOGGER.debug(f'DEFINE settings for {service_id} property: {property_id} '
        #                   f'validator: {type(validator)}')
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        assert not isinstance(service_id, StrEnum), 'service_id must NOT be StrEnum'
        assert not isinstance(property_id, StrEnum), 'property_id must NOT be StrEnum'

        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            settings_for_service = {}
            cls.service_to_settings_map[service_id] = settings_for_service
            MY_LOGGER.debug(f'Added service_id: {service_id} settings_for_service '
                            f'{settings_for_service}')
        #
        # Allow to override any previous entry since doing otherwise would complicate
        # initialization order since it is normal to initialize your ancestor
        # prior to yourself

        if validator is None:
            settings_for_service.pop(property_id, None)
            MY_LOGGER.debug(f'Undefining setting {property_id} from {service_id}')
        else:
            settings_for_service[property_id] = validator
            MY_LOGGER.debug(f'Defining setting {property_id} for {service_id}')


    @classmethod
    def is_setting_available(cls, service_id: str, property_id: str) -> bool:
        return cls.is_valid_property(service_id, property_id)

    @classmethod
    def is_valid_property(cls, service_id: str, property_id: str) -> bool:
        """
        Note that this can give FALSE results during startup, when the settings
        have not yet all been defined. This should be benign since things should
        return to normal after the settngs are defined, which should be quick.

        :param service_id:
        :param property_id:
        :return:
        """
        if property_id is None:
            property_id = ''
        # MY_LOGGER.debug(f'service_id: {service_id} property_id: {property_id}')
        assert isinstance(service_id, str), 'Service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        if not service_id or len(service_id) == 0:
            if property_id == SettingsProperties.ENGINE:
                return True

        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            # MY_LOGGER.debug(f'No settings for {service_id}')
            return False

        if property_id not in settings_for_service.keys():
            if MY_LOGGER.isEnabledFor(DEBUG_V):
                MY_LOGGER.debug(f'{property_id} not in {service_id} settings: '
                                  f'{settings_for_service.keys()}')
            return False
        return True

    @classmethod
    def get_const_value(cls, service_id: str, property_id: str) -> Any | None:
        """
        Some settings are a fixed value, depeding upon service capabilities.
        For example, services which download voice really need a cache to be
        performant. Also, can't adjust volume (let player do it).

        This method primarily needed during loading of raw settings from settings.xml.
        The loading occurs AFTER settings are defined (which defines the constant values).
        Therefor after loading the settings, this is called to correct any conflicts.

        :param service_id:
        :param property_id:
        :return: None if the setting is not constant, otherwise the fixed value
        """

        val: IValidator = cls.get_validator(service_id, property_id)
        if val is None:
            return None
        return val.get_const_value()  # Returns None if not constant

    @classmethod
    def get_validator(cls, service_id: str,
                      property_id: str) -> (IBoolValidator | IStringValidator |
                                            IIntValidator | IStrEnumValidator |
                                            IConstraintsValidator |
                                            IGenderValidator | INumericValidator |
                                            IChannelValidator | None):
        if property_id is None:
            property_id = ''
        assert isinstance(service_id, str), 'service_id must be a str'
        assert isinstance(property_id, str), 'property_id must be a str'
        assert not isinstance(service_id, StrEnum), 'service_id must NOT be StrEnum'
        assert not isinstance(property_id, StrEnum), 'property_id must NOT be StrEnum'
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_id)
        if settings_for_service is None:
            return None
        validator = settings_for_service.get(property_id)
        return validator

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
                           property_id: str) -> List[AllowedValue] | None:
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
