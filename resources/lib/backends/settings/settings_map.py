# coding=utf-8
from __future__ import annotations  # For union operator |

from logging import DEBUG
from pathlib import Path
from typing import Union

from backends.settings.service_types import ServiceID, SERVICES_BY_TYPE

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import (AllowedValue, IBoolValidator,
                                            IChannelValidator,
                                            IConstraintsValidator,
                                            IEngineValidator, IGenderValidator,
                                            IIntValidator,
                                            INumericValidator, ISimpleValidator,
                                            IStrEnumValidator,
                                            IStringValidator, IValidator)
from backends.settings.service_types import ServiceType
from common.logger import BasicLogger, DEBUG_V

MY_LOGGER = BasicLogger.get_logger(__name__)


class Reason(StrEnum):
    """

    """
    UNKNOWN = 'unknown'
    AVAILABLE = 'available'  # Appears fully functional
    NOT_SUPPORTED = 'not_supported'  # Not supported on this platform
    NOT_AVAILABLE = 'not_available'  # Not installed, not found, etc.
    BROKEN = 'broken'  # Command found, but not runnable


class SettingsMap:
    """
    A map of all possible settings and their type.

    This is needed since we have our own settings GUI and don't rely on
    settings.xml having every setting name and type info (can't easily access it
    anyway), we instead depend on this map as well as validators, constraints, etc.

    The setting names are nearly the same between the different engines, etc., but
    not identical. The Settings class creates default values, but in order to do this
    it needs to reliably know: 1) the properties, 2) at least the
    default values. Better yet, if it knows 3) which values are valid.

    Settings are kept in a two-level map. The first level maps the setting_id to
    a secondary map of that service's settings.
    """

    # Maps a service ('eSpeak') to map of its settings.
    # Service and setting ids are defined in settings_constants.

    # These maps are built by the services themselves. They are defined at startup.
    # Note that only settings of type string, integer and boolean are defined,
    # more can be added, as needed. More complex types such as float and lists of
    # the basic types are supported by Kodi, but since it complicates users from
    # reading settings.xml, those types are avoided. Floats are emulated by
    # storing values as integers, but scaling them as needed for UI presentation

    # service_to_settings_map maps a particular service to a map of its settings and
    # any validator associated with that setting.
    # Note that the only difference between settings and properties are that
    # properties are values that are not persisted in settings.xml, etc. Settings
    # are almost always persisted in settings.xml.
    #
    # Dict[unique_service_id, Dict[service_property, Validator]]
    # Ex [googleTTS, [volume]] = volume_validator
    service_to_settings_map: Dict[str, Dict[str, IValidator]] = {}

    # service_type_to_svcs_map maps a ServiceType into all services
    # of that type.
    # service_type_to_svcs_map: Dict[ServiceType, List[ServiceID]] = {}

    # service_key_to_val_map is similar to service_to_settings_map, above.
    # service_key_to_val maps a service setting or property to any validator
    # associated with it.
    service_key_to_val_map: Dict[ServiceID, IValidator | None] = {}

    # service_availability_map holds the most recent availability status of a
    # given service.
    service_availability_map: Dict[str, Reason] = {}

    # service_to_properties_map maps a service (without property id) to a map of
    # the service's properties to its initial values. Note that property ids do
    # not have to be a SettingProp

    #   service_to_properties_map: Dict[ServiceID, Dict[ServiceID, Any]] = {}

    # service_type_to_properties_map maps a ServiceType to an index of all services
    # of that ServiceType, with the value of the index entry referencing a map
    # of all settings of that service.
    #
    service_type_to_properties_map: Dict[ServiceType, Dict[ServiceID, Dict[str, Any]]] = {}

    # structure to get from an instance of a service_type to an instance of
    # another service type. Used by DependencyValidator. Here, called
    # src_to_cand_svc, or service-to-candidate-services.
    #
    # Like with Settings, a key is formed from the service_type and
    # setting_id: ex setting_id.service_type. But in this case there
    # are two levels of lookup
    #   Dict[setting_id.service_type] -> Dict[dep_service_type]
    #     -> List[dep_service_id]
    #
    # Example, EngineType GoogleTTS is able to use specific instances
    svc_to_cand_svc: Dict[ServiceID, Dict[ServiceID, List[str]]] = {}

    #
    # TODO: Eliminate service_to_service_type_map with apis that specify both
    # or that encode both in name "engine.google' "player_key.engine.google'
    #  service_to_service_type_map: Dict[str, ServiceType] = {}

    '''
    @classmethod
    def define_service_properties(cls, service_key: ServiceID,
                                  service_properties: Dict[str, Any]):
        """
        Defines the properties with initial values for a service. Examples
        include name, max_phrase_length, cache_suffix. It does NOT
        specify the settings the service has (ex. an engine's player_key is NOT
        a property of the service, it is a setting). (See define_setting)

        :param service_key: Identifies the ServiceType and the service.
        :param service_properties: Dict[property_name, initial_value]
        :return:
        """
        try:
            # service_properties is from one Service.

            # Each entry in service_type_to_properties_map is a map of every
            # property that is a member of the same service_type.
            props_for_service_type: Dict[ServiceID, Dict[str, Any]]
            props_for_service_type = cls.service_type_to_properties_map.setdefault(
                    service_key.service_type, {})
            for prop, value in service_properties.items():
                assert isinstance(prop, str), 'prop must be a str'
                assert not isinstance(prop,
                                      StrEnum), 'prop must NOT be StrEnum'
                # Add property to validator map (if it doesn't already exist
                # (and with no validator),

                prop_key: ServiceID = service_key.with_prop(prop)
                cls.service_key_to_val_map.setdefault(prop_key, None)
                # All properties from a single service go into the index
                # service_key
                props_for_service_type[prop_key] = value
            # Also keep all properties for a service into another map indexed
            # by service_key
            cls.service_to_properties_map[service_key] = props_for_service_type
            MY_LOGGER.debug(f'props_for_service_type: {props_for_service_type}')
        except Exception as e:
            MY_LOGGER.exception('')
    '''

    @classmethod
    def get_srvc_props_for_service_type(cls, service_type: ServiceType) \
            -> List[Tuple[ServiceID, str]]:
        """
          Returns a list of service properties that have registered via
          SettingsMap.define_service_properties(ServiceType.xxx, serviceID, properties)

          Useful for finding the engines that work with TTS, etc.
        :param service_type:
        :return: A Tuple [setting_id, name] Where name is the value of
                 any property named 'name' when this was defined, or
                 with name having a message indicating the name was not specified.
        """
        service_props: List[Tuple[ServiceID, str]] = []
        service_dict: Dict[ServiceID, Any]
        service_dict = cls.service_type_to_properties_map.get(service_type, {})
        service_key: ServiceID
        for service_key in service_dict.keys():
            # Just want the service, without the setting id
            name: str = service_dict.get(service_key)

            # name: str = service_dict.setdefault('name', 'No name given')
            #  MY_LOGGER.debug(f'service_key: {service_key} name: {name}')
            service_props.append((service_key, name))
        return service_props

    '''
    @classmethod
    def get_service_type_for_service(cls, service_id: str) -> ServiceType | None:
        #  TODO- Eliminate. Not needed with ServiceID
        return cls.service_to_service_type_map.get(service_id)
    '''

    '''
    @classmethod
    def get_service_properties(cls, service_key: ServiceID) -> Dict[ServiceID, Any]:
        """
        Gets the properties for the given service_key (service_type, service_id).

        :param service_key: defines the service (service_type and service_id)
                            that the properties belong
        :return:
                Note that property names do not need to be defined in SettingProp
        """
        service_props: Dict[ServiceID, Any]
        service_props = cls.service_to_properties_map.setdefault(service_key, {})
        return service_props

    @classmethod
    def get_service_property(cls, key: ServiceID, property_id: str | Path) -> Any:
        properties: Dict[ServiceID, Any] = cls.get_service_properties(key)
        return properties.get(key.with_prop(property_id), None)
    '''

    '''
    @classmethod
    def get_available_property_ids(cls, service_type: ServiceType) -> List[Tuple[
                            ServiceID, Dict[str, Any]]] | None:
        """
        Creates list of all properties (prop-name and value) for all services
        of the given ServiceType
        :param service_type:
        :return: A List of (ServiceID, Dict[property_id, property_value])
                 where: ServiceID is a service of service_type that has
                        called define_service_properties to define properties.
                and Dict[property, property_value] are the properties and values
                defined in define_service_properties.
        """
        if not ServiceType.ALL.value <= service_type.value <= \
               ServiceType.LAST_SERVICE_TYPE.value:
            MY_LOGGER.debug(f'Invalid ServiceType: {service_type}')
            return None

        cls.get_srvc_props_for_service_type(service_type=service_type)
        service_props: Dict[str, Any]
        available_service_ids: List[Tuple[ServiceID, Dict[str, Any]]] = []
        for service_key, service_props in cls.service_to_properties_map.items():
            if service_key.setting_id is not None:
                raise ValueError(f'Expected a Service, NOT a setting: {service_key}')
            if service_key.service_type == service_type:
                if cls.service_availability_map.get(service_key.service_key,
                                                    Reason.UNKNOWN) == Reason.AVAILABLE:
                    available_service_ids.append((service_key, service_props))
        return available_service_ids
    '''

    @classmethod
    def get_available_services(cls, service_type: ServiceType | None) -> List[ServiceID]:
        """
        Retrieves the id of available services of the given service_type, or all types
        if omitted. Settings are not returned, just services.

        :param service_type:
        :return:
        """
        result: List[ServiceID] = []
        service_types: List[ServiceType]
        if service_type is None:  # Get all service Types
            service_types = list(ServiceType)
        else:
            service_types = [service_type]
        # MY_LOGGER.debug(f'service_types: {service_types}')
        for service_type in service_types:
            service_type: ServiceType
            for service_id in SERVICES_BY_TYPE[service_type]:
                service_id: StrEnum
                service_key: ServiceID = ServiceID(service_type, service_id)
                # MY_LOGGER.debug(f'service_key: {service_key} # keys:'
                #                 f' {cls.service_availability_map.keys()}')
                # MY_LOGGER.debug(f'{cls.service_availability_map.get(service_key.service_key)}')
                if cls.service_availability_map.get(service_key.service_key,
                                                    Reason.UNKNOWN) == Reason.AVAILABLE:
                    result.append(service_key)
        #  MY_LOGGER.debug(f'result: {result}')
        return result


    @classmethod
    def set_is_available(cls, key: ServiceID, reason: Reason) -> None:
        # MY_LOGGER.debug(f'key: {key}')
        if reason != Reason.AVAILABLE:
            MY_LOGGER.debug(f'{key.service_key} is NOT available reason: {reason}')
        # else:
        #     MY_LOGGER.debug(f'{key.service_key} is available')
        # Make sure the key ONLY contains ServiceType and Service id
        cls.service_availability_map[key.service_key] = reason

    @classmethod
    def is_available(cls, key: ServiceID) -> bool:
        reason: Reason
        reason = cls.service_availability_map.get(key.with_prop(None).service_key, None)
        if reason is None:
            return True
            # MY_LOGGER.debug(f'{setting_id} availability UNKNOWN')
            # cls.set_is_available(setting_id, Reason.UNKNOWN)
            # return False

        if reason == Reason.AVAILABLE:
            return True
        MY_LOGGER.debug(f'{key} is NOT available reason: {reason}')
        return False

    @classmethod
    def define_setting(cls, service_key: ServiceID,
                       validator: IValidator | None):
        """
        Defines a validator to use for a given setting of a service
        :param service_key: Identifies the service_type, service and setting_id
        :param validator: If None, then the setting is NOT supported and any
                          prior definition is removed.
        """
        # MY_LOGGER.debug(f'DEFINE settings for {setting_id} property: {setting_id} '
        #                 f'validator: {type(validator)}')

        #  MY_LOGGER.debug(f'service_key: {service_key}')
        settings_for_service: Dict[str, IValidator]
        settings_for_service = (
            cls.service_to_settings_map.setdefault(service_key.service_key, {}))
        #  MY_LOGGER.debug(f'service_to_settings for: '
        #                  f'{service_key.service_key} \n service_to_settings_map: '
        #                  f'{cls.service_to_settings_map}')

        # Don't add stupid None entry for the ServiceID id without any setting_id
        # in it, that is, the entry that acts like the root node for that service.
        # TODO: is such a 'root node' even required? The info it has is contained
        #       in each setting. Also, adding a setting, creates settings_for_service.
        if True:  # service_key.setting_id is not None:
            #
            # Allow to override any previous entry since doing otherwise would complicate
            # initialization order since it is normal to initialize your ancestor
            # prior to yourself

            if validator is None:
                settings_for_service.pop(service_key.setting_id, None)
                MY_LOGGER.debug(f'Undefining setting {service_key.setting_id}'
                                f' from {service_key}')
                cls.service_key_to_val_map[service_key] = None
            else:
                cls.service_key_to_val_map.setdefault(service_key, validator)
                settings_for_service[service_key.setting_id] = validator
                #  MY_LOGGER.debug(f'Defining setting: '
                #                  f'{service_key} \n'
                #                  f'settings_for_service: {settings_for_service}')

    @classmethod
    def is_setting_available(cls, key: ServiceID, property_id: str) -> bool:
        assert isinstance(property_id, str), 'setting_id must be a str'
        assert not isinstance(property_id, StrEnum), 'setting_id must NOT be StrEnum'

        return cls.is_valid_setting(key)

    @classmethod
    def is_valid_setting(cls, key: ServiceID) -> bool:
        """
        Note that this can give FALSE results during startup, when the settings
        have not yet all been defined. This should be benign since things should
        return to normal after the settngs are defined, which should be quick.

        :param key:
        :return:
        """
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(key.service_key)
        if settings_for_service is None:
            MY_LOGGER.debug(f'No settings for {key.setting_path} {key.service_key}')
            return False

        if key.setting_id not in settings_for_service.keys():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{key.setting_id} not in settings')
            return False
        #  if MY_LOGGER.isEnabledFor(DEBUG):
        #      MY_LOGGER.debug(f'{key.setting_id} is VALID because in {key} setting: '
        #                      f'{settings_for_service.get(key.setting_id)}')
        return True

    @classmethod
    def get_const_value(cls, service_key: ServiceID) -> Any | None:
        """
        Some settings are a fixed value, depending upon service capabilities.
        For example, services which download voice really need a cache to be
        performant. Also, can't adjust volume (let player_key do it).

        This method primarily needed during loading of raw settings from settings.xml.
        The loading occurs AFTER settings are defined (which defines the constant values).
        Therefore, after loading the settings, this is called to correct any conflicts.

        :param service_key:
        :return: None if the setting is not constant, otherwise the fixed value
        """

        val: IValidator = cls.get_validator(service_key)
        if val is None:
            return None
        return val.get_const_value()  # Returns None if not constant

    '''
    @classmethod
    def get_service_settings(cls, service_key: ServiceID) ->\
            List[Tuple[ServiceID, Union[
                IBoolValidator, IStringValidator, IIntValidator, IStrEnumValidator,
                IConstraintsValidator, IGenderValidator, INumericValidator,
                IChannelValidator, IEngineValidator, None]]]:
        """
        Similar to get_validator, returns any validator found for a setting.
        Raises ValueError if setting not
        :param service_key:
        :return: Validator, if one has been defined for this setting.
                 None if setting exists, but no validator defined
        """
        result: List[Tuple[ServiceID,
                           Union[IBoolValidator, IStringValidator, IIntValidator,
                                 IStrEnumValidator, IConstraintsValidator,
                                 IGenderValidator, INumericValidator,
                                 IChannelValidator, IEngineValidator, None]]] = []
        properties: Dict[ServiceID, Any] = cls.get_service_properties(service_key)
        for property_key in properties.keys():
            property_key: ServiceID
            val: Union[IBoolValidator, IStringValidator, IIntValidator,
                       IStrEnumValidator,
                       IConstraintsValidator, IGenderValidator, INumericValidator,
                       IChannelValidator, IEngineValidator, None]
            try:
                val = cls.service_key_to_val_map[property_key]
                result.append((property_key, val))
            except:
                MY_LOGGER.exception('')
        return result
    '''

    @classmethod
    def get_validator(cls,
                      service_key: ServiceID) -> (IBoolValidator |
                                                  IStringValidator |
                                                  IIntValidator |
                                                  IStrEnumValidator |
                                                  IConstraintsValidator |
                                                  IGenderValidator |
                                                  INumericValidator |
                                                  IChannelValidator |
                                                  IEngineValidator |
                                                  ISimpleValidator | None):
        #  MY_LOGGER.debug(f'service_key: {service_key}')
        settings_for_service: Dict[str, IValidator]
        settings_for_service = cls.service_to_settings_map.get(service_key.service_key)
        #  MY_LOGGER.debug(f'service_key: {service_key}'
        #                  f' settings_for_service: {settings_for_service}')
        if settings_for_service is None:
            return None
        validator = settings_for_service.get(service_key.setting_id)
        return validator

    @classmethod
    def get_constraints(cls, key: ServiceID) -> IConstraints:
        validator: IConstraintsValidator
        validator = cls.get_validator(key)
        constraints: IConstraints
        constraints = validator.constraints
        return constraints

    @classmethod
    def get_default_value(cls, key: ServiceID) -> int | bool | str | float | None:
        validator: IValidator = cls.get_validator(key)
        if validator is None:
            return None
        return validator.default

    @classmethod
    def get_allowed_values(cls, key: ServiceID) -> List[AllowedValue] | None:
        validator: IValidator = cls.get_validator(key)
        if validator is None:
            return None
        if not isinstance(validator, IStringValidator):
            return None
        validator: IStringValidator
        return validator.get_allowed_values()

    @classmethod
    def get_value(cls, key: ServiceID,
                  property_id: str) -> int | bool | float | str | None:
        if property_id is None:
            property_id = ''
        assert isinstance(property_id, str), 'setting_id must be a str'
        assert not isinstance(property_id, StrEnum), 'setting_id must NOT be StrEnum'
        validator: IValidator = cls.get_validator(key)
        if validator is None:
            return None
        value = validator.get_tts_value()
        return value
