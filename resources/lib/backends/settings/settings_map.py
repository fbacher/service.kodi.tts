# coding=utf-8
from __future__ import annotations  # For union operator |

from backends.settings.service_types import ALL_ENGINES, ServiceID, SERVICES_BY_TYPE
from backends.settings.setting_properties import SettingProp, SettingType
from common.service_status import Progress, ServiceStatus, Status, StatusType

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
from common.logger import *

MY_LOGGER: BasicLogger = BasicLogger.get_logger(__name__)


class ServiceInfo:
    """
    Contains information about the given service or service property. The information
    includes:
        Type of the service or service property,
        status of the service (does not apply to a service's property)
        validator, if any
    """
    def __init__(self, service_id: ServiceID,
                 property_type: SettingType | None,
                 service_status: StatusType = StatusType.UNCHECKED,
                 validator: (IBoolValidator |
                             IChannelValidator |
                             IConstraintsValidator |
                             IEngineValidator | IGenderValidator |
                             IIntValidator |
                             INumericValidator | ISimpleValidator |
                             IStrEnumValidator |
                             IStringValidator | IValidator | None) = None,
                 persist: bool = True):
        """
        :param service_id: Fully qualified id for the service, or service's property
        :param property_type: Type of service's property
        :param service_status: Status of the service (working, broken, unknown, etc.)
        :param validator: Any validator associated with this service
        :param persist: If True, then the value is saved in settings.xml, otherwise
                        the value is not saved.
        """
        if property_type is None:
            if validator is None or validator.property_type is None:
                MY_LOGGER.warning(f'property_type not specified and not found in '
                                  f'validator for service: {service_id} validator:'
                                  f' {type(validator)}')
            else:
                property_type = validator.property_type
        self._service_id: ServiceID = service_id
        self._property_type: SettingType | None = property_type
        self._service_status: StatusType = service_status
        self._validator: (IBoolValidator |
                          IChannelValidator |
                          IConstraintsValidator |
                          IEngineValidator | IGenderValidator |
                          IIntValidator |
                          INumericValidator | ISimpleValidator |
                          IStrEnumValidator |
                          IStringValidator | IValidator | None) = validator
        self._persist: bool = persist

    @property
    def service_id(self) -> ServiceID:
        return self._service_id

    @property
    def property_type(self) -> SettingType | None:
        return self._property_type

    @property
    def service_status(self) -> StatusType:
        return self._service_status

    @service_status.setter
    def service_status(self, service_status: StatusType) -> None:
        self._service_status = service_status

    @property
    def validator(self) -> (IBoolValidator |
                            IChannelValidator |
                            IConstraintsValidator |
                            IEngineValidator | IGenderValidator |
                            IIntValidator |
                            INumericValidator | ISimpleValidator |
                            IStrEnumValidator |
                            IStringValidator | IValidator | None):
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self.service_id} validator: {self._validator}')
        return self._validator

    @property
    def persist(self) -> bool:
        return self._persist

    def __repr__(self) -> str:
        val_str: str = ''
        if self.validator is not None:
            val_str = self.validator.__class__.__name__
        return (f'service: {self.service_id} type: {self.property_type} '
                f'status: {self.service_status} persist: {self.persist} '
                f'val: {val_str}')


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

    Settings are kept in a two-level map. The first level maps the service_id to
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
    service_to_settings_map: Dict[str, Dict[str, ServiceInfo]] = {}

    # service_type_to_svcs_map maps a ServiceType into all services
    # of that type.
    # service_type_to_svcs_map: Dict[ServiceType, List[ServiceID]] = {}

    # service_key_to_val_map is similar to service_to_settings_map, above.
    # service_key_to_val maps a service setting or property to any validator
    # associated with it.
    # service_key_to_val_map: Dict[ServiceID, IValidator | None] = {}

    service_info_map: Dict[str, ServiceInfo] = {}

    # service_availability_map holds the most recent availability status of a
    # given service.
    # service_availability_map: Dict[str, ServiceStatus] = {}

    # service_to_properties_map maps a service (without property id) to a map of
    # the service's properties to its initial values. Note that property ids do
    # not have to be a SettingProp

    #   service_to_properties_map: Dict[ServiceID, Dict[ServiceID, Any]] = {}

    # service_type_to_properties_map maps a ServiceType to an index of all services
    # of that ServiceType, with the value of the index entry referencing a map
    # of all settings of that service.
    #
    # service_type_to_properties_map: Dict[ServiceType, Dict[ServiceID, Dict[str, Any]]] = {}

    # structure to get from an instance of a service_type to an instance of
    # another service type. Used by DependencyValidator. Here, called
    # src_to_cand_svc, or service-to-candidate-services.
    #
    # Like with Settings, a key is formed from the service_type and
    # service_id: ex service_id.service_type. But in this case there
    # are two levels of lookup
    #   Dict[service_id.service_type] -> Dict[dep_service_type]
    #     -> List[dep_service_id]
    #
    # Example, EngineType GoogleTTS is able to use specific instances
    svc_to_cand_svc: Dict[ServiceID, Dict[ServiceID, List[str]]] = {}

    @classmethod
    def get_available_services(cls, service_type: ServiceType | None) -> List[ServiceID]:
        """
        Retrieves the id of available services of the given service_type, or all types
        if omitted. Settings are not returned, just services.

        For Engine and Player types, the results are in Engine or Player preference
        order.

        :param service_type:
        :return:
        """
        result: List[ServiceID] = []
        service_types: List[ServiceType]  # Engine, player, etc.
        if service_type is None:  # Get all service Types
            service_types = list(ServiceType)
        else:
            service_types = [service_type]
        for service_type in service_types:
            service_type: ServiceType
            for service_key in SERVICES_BY_TYPE[service_type]:
                # For engine and player types, these are in preference order.
                # Therefore, the returned available values will be in preference order
                # example: service_key Engine.google, Engine.espeak, player.mpv
                # Does NOT include tts.tts.*
                service_key: StrEnum
                service_id: ServiceID = ServiceID(service_type, service_key,
                                                  SettingProp.SERVICE_ID)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'service_type: {service_type} '
                                    f'service_key: {service_key} \n'
                                    f'service_id: {service_id} '
                                    f'service_id.key: {service_id.key}')
                # if MY_LOGGER.isEnabledFor(DEBUG_XV):
                #     MY_LOGGER.debug_xv(f'service_key: {service_key} # keys:'
                #                        f' {cls.service_info_map.keys()}')
                service_info: ServiceInfo
                service_info = cls.service_info_map.get(service_id.key)
                if service_info is None:
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'No ServiceInfo found for {service_id.key}')
                    continue
                service_status: StatusType = service_info.service_status

                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'availability: key: '
                                    f'{service_id.key} '
                                    f'status: {service_status}')
                if service_status is not None and service_status == StatusType.OK:
                    result.append(service_id)
        return result

    @classmethod
    def set_available(cls, service_id: ServiceID,
                      status: StatusType = StatusType.OK) -> None:
        """
        Sets the current status of the given service.

        :param service_id: Identifies the service
        :param status:
        :return:
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'key: {service_id.key} status: {status}')
        if status is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{service_id.key} is NOT available -'
                                f' status None')
            return
        elif status != StatusType.OK:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{service_id.key} is NOT available status'
                                f'status: {status}')
        service_info: ServiceInfo = cls.service_info_map.get(service_id.key)
        if service_info is None:
            service_info = ServiceInfo(service_id, property_type=SettingType.STRING_TYPE,
                                       service_status=status,
                                       validator=None,
                                       persist=False)
        else:
            service_info.service_status = status
        cls.service_info_map[service_id.key] = service_info

    @classmethod
    def is_available(cls, service_id: ServiceID, force: bool = False) -> bool:
        """
        Determine if the SERVICE for the given setting is available. Ex. for the
        setting engine.google.player, the SERVICE is engine.google

        If the SERVICE is not available, then neither are any of its settings

        :param service_id:
        :param force:
        :return:
        """
        service_info: ServiceInfo
        service_info = cls.service_info_map.get(service_id.key, None)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{service_id} force: {force} service: '
                            f'{service_id.key} '
                            f'service_info: {service_info}')
        service_status: StatusType = StatusType.UNCHECKED
        if service_info is None:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'service_info is None force: {force}')
                MY_LOGGER.debug(f'{service_id} is NOT registered.')
            return False
        else:
            service_status = service_info.service_status
        if service_status != StatusType.OK:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{service_id.key} is NOT available '
                                f'status: {service_status}')
            return False
        return True

    @classmethod
    def define_setting(cls, service_id: ServiceID,
                       setting_type: SettingType | None = None,
                       service_status: StatusType | None = StatusType.OK,
                       validator: (IBoolValidator |
                                   IChannelValidator |
                                   IConstraintsValidator |
                                   IEngineValidator | IGenderValidator |
                                   IIntValidator |
                                   INumericValidator | ISimpleValidator |
                                   IStrEnumValidator |
                                   IStringValidator | IValidator | None) = None,
                       persist: bool = True):
        """
        Defines a property of a service
        :param service_id: Identifies the service_type and service id. For
        a service property, then also includes the property_id
        :param setting_type: Identifies the type of service property
        :param service_status: Indicates whether the service is available, not
        yet determined, etc. Does NOT apply to service properties
        :param validator: Specifies any validator used, otherwise no validation is
        performed
        :param persist: When True, values are persisted in settings.xml.
        """
        # MY_LOGGER.debug(f'DEFINE settings for {service_id} property: {service_id} '
        #                 f'validator: {type(validator)}')

        #  MY_LOGGER.debug(f'service_key: {service_key}')
        settings_for_service: Dict[str, ServiceInfo]
        settings_for_service = (
            cls.service_to_settings_map.setdefault(service_id.key, {}))
        #  MY_LOGGER.debug(f'service_to_settings for: '
        #                  f'{service_key.key} \n service_to_settings_map: '
        #                  f'{cls.service_to_settings_map}')

        # Don't add stupid None entry for the ServiceID id without any service_id
        # in it, that is, the entry that acts like the root node for that service.
        service_info = cls.service_info_map.get(service_id.key)
        if service_info is not None:
            if MY_LOGGER.isEnabledFor(WARNING):
                MY_LOGGER.warning(f'Service {service_id} already defined. Ignoring '
                                  f'redefinition')
                return
        service_info = ServiceInfo(service_id, property_type=setting_type,
                                   service_status=service_status,
                                   validator=validator,
                                   persist=persist)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Defining {service_id} '
                            f'service_info: {service_info}')
        cls.service_info_map[service_id.key] = service_info
        settings_for_service[service_id.key] = service_info

    @classmethod
    def is_setting_available(cls, service_id: ServiceID, property_id: str) -> bool:
        assert isinstance(property_id, str), 'property_id must be a str'
        assert not isinstance(property_id, StrEnum), 'property_id must NOT be StrEnum'

        return cls.is_valid_setting(service_id)

    @classmethod
    def is_valid_setting(cls, service_id: ServiceID) -> bool:
        """
        Verfies that a setting has been explicitly defined.

        Note that this can give FALSE results during startup, when the settings
        have not yet all been defined. This should be benign since things should
        return to normal after the settngs are defined, which should be quick.

        :param service_id:
        :return:
        """
        # Verify that
        if service_id.key not in cls.service_info_map.keys():
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'{service_id.key} not in service_info_map')
            return False
        return True

    @classmethod
    def get_setting_type(cls, service_id: ServiceID) -> SettingType:
        service_info: ServiceInfo | None = cls.service_info_map.get(service_id.key)
        if service_info is None:
            raise ValueError(f'Invalid service_id: {service_id}')
        return service_info.property_type

    @classmethod
    def get_const_value(cls, service_id: ServiceID) -> Any | None:
        """
        Some settings are a fixed value, depending upon service capabilities.
        For example, services which download voice really need a cache to be
        performant. Also, can't adjust volume (let player_key do it).

        This method primarily needed during loading of raw settings from settings.xml.
        The loading occurs AFTER settings are defined (which defines the constant values).
        Therefore, after loading the settings, this is called to correct any conflicts.

        :param service_id:
        :return: None if the setting is not constant, otherwise the fixed value
        """

        val: IValidator = cls.get_validator(service_id)
        if val is None:
            return None
        return val.get_const_value()  # Returns None if not constant

    @classmethod
    def get_validator(cls,
                      service_id: ServiceID) -> (IBoolValidator |
                                                  IStringValidator |
                                                  IIntValidator |
                                                  IStrEnumValidator |
                                                  IConstraintsValidator |
                                                  IGenderValidator |
                                                  INumericValidator |
                                                  IChannelValidator |
                                                  IEngineValidator |
                                                  ISimpleValidator | None):
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'service_id: {service_id} key: {service_id.key}')
        service_info: ServiceInfo = cls.service_info_map.get(service_id.key)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'service_info: {service_info}')
        if service_info is None:
            return None
        validator = service_info.validator
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'validator: {validator}')
        return validator

    @classmethod
    def get_constraints(cls, service_id: ServiceID) -> IConstraints:
        validator: IConstraintsValidator
        validator = cls.get_validator(service_id)
        constraints: IConstraints
        constraints = validator.constraints
        return constraints

    @classmethod
    def get_default_value(cls, service_id: ServiceID) -> int | bool | str | float | None:
        validator: IValidator = cls.get_validator(service_id)
        if validator is None:
            return None
        return validator.default

    @classmethod
    def get_allowed_values(cls, service_id: ServiceID) -> List[AllowedValue] | None:
        validator: IValidator = cls.get_validator(service_id)
        if validator is None:
            return None
        if not isinstance(validator, IStringValidator):
            return None
        validator: IStringValidator
        return validator.get_allowed_values()

    @classmethod
    def get_value(cls, service_id: ServiceID,
                  property_id: str) -> int | bool | float | str | None:
        if property_id is None:
            property_id = ''
        assert isinstance(property_id, str), 'property_id must be a str'
        assert not isinstance(property_id, StrEnum), 'property_id must NOT be StrEnum'
        validator: IValidator = cls.get_validator(service_id)
        if validator is None:
            return None
        value = validator.get_tts_value()
        return value
