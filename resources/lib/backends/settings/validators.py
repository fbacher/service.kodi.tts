# coding=utf-8
from __future__ import annotations  # For union operator |

import enum
import math

from backends.settings.setting_properties import SettingType
from common import *

from backends.settings.constraints import Constraints
from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import (AllowedValue, IChannelValidator,
                                            IGenderValidator,
                                            ISimpleValidator, IStringValidator,
                                            IValidator, UIValues)
from backends.settings.service_types import ServiceKey, Services, ServiceType
from backends.settings.settings_map import Status, SettingsMap
from backends.settings.service_unavailable_exception import ServiceUnavailable
from common.logger import *
from common.service_status import StatusType
from common.setting_constants import AudioType, Channels, Genders
from common.settings_low_level import SettingsLowLevel
from backends.settings.service_types import ServiceID

MY_LOGGER = BasicLogger.get_logger(__name__)


class ConvertType(enum.Enum):
    NONE = enum.auto()
    PERCENT = enum.auto()
    DECIBELS = enum.auto()


class Validator(IValidator):

    """
    Validators are helpers for getting and setting values. The validator can verify
    that the values are valid, supply defaults and be queried for what value choices
    there are. In addition,
    """

    def __init__(self, service_key: ServiceID,
                 property_type: SettingType,
                 default: Any | None = None, const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        self._default = None
        super().__init__(service_key, property_type)
        self._service_key: ServiceID = service_key
        self._property_type: SettingType = property_type
        self.const: bool = const
        self.tts_validator: IValidator | None = None
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    @property
    def property_type(self) -> SettingType:
        return self._property_type

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=self._property_type,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        return None

    def get_tts_validator(self) -> IValidator:
        if self.tts_validator is None:
            if self.service_key.service_id == Services.TTS_SERVICE:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'current_key: {self.service_key} \n'
                                    f'service_id: {self.service_key.service_id}')
                return self
        try:
            tts_key: ServiceID
            tts_key = ServiceKey.TTS_KEY.with_prop(self.service_key.setting_id)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'tts_key: {tts_key}')
            tts_val = SettingsMap.get_validator(tts_key)
            self.tts_validator = tts_val
        except Exception:
            MY_LOGGER.exception('')
        return self.tts_validator


class BaseNumericValidator(Validator):

    def __init__(self, service_key: ServiceID,
                 minimum: int, maximum: int,
                 default: int | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 increment: int | float = 0.0,
                 const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        property_type: SettingType = SettingType.INTEGER_TYPE
        if not is_integer:
            property_type = SettingType.FLOAT_TYPE
        super().__init__(service_key, property_type, const=const,
                         define_setting=define_setting,
                         service_status=service_status,
                         persist=persist)
        self._service_key: ServiceID = service_key
        self.minimum: int = minimum
        self.maximum: int = maximum
        self._default = default
        self.is_decibels: bool = is_decibels
        MY_LOGGER.debug(f'is_decibels: {is_decibels} self: {self.is_decibels}')
        self.is_integer = is_integer
        if increment is None or increment <= 0.0:
            increment = (maximum - minimum) / 20.0
        self._increment = increment
        self.const: bool = const
        return

    @property
    def property_type(self) -> SettingType:
        return super().property_type

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default

    @classmethod
    def to_percent(cls, value: int | float) -> float:
        """
        Converts the value from decibels to percent.

        :return:
        """
        result = 100 * (10 ** (value / 20.0))
        return result

    @classmethod
    def to_decibels(cls, value) -> float:

        result: float = 10.0 * math.log10(float(value) / 100.0)
        return result

    @property
    def increment(self) -> int:
        if self.const:
            return 0
        return self._increment

    @property
    def default(self) -> int:
        return self._default


class TTSNumericValidator(BaseNumericValidator):

    def __init__(self, service_key: ServiceID,
                 minimum: int | float, maximum: int | float,
                 default: int | float | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 internal_scale_factor: int | float = 1,
                 increment: int | float = 0.0,
                 const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        MY_LOGGER.debug(f'is_decibels: {is_decibels}')
        super().__init__(service_key=service_key,
                         minimum=minimum,
                         maximum=maximum,
                         default=default,
                         is_decibels=is_decibels,
                         is_integer=is_integer,
                         increment=increment,
                         const=False,
                         define_setting=define_setting,
                         service_status=service_status,
                         persist=persist)
        MY_LOGGER.debug(f'is_decibels: {is_decibels}')
        try:
            MY_LOGGER.debug(f'self.is_decibels: {self.is_decibels}')
        except:
            MY_LOGGER.exception('')
        self.is_decibels = is_decibels
        self.internal_scale_factor: int | float = internal_scale_factor
        if const:
            self.set_value(default)
            super().const = const
            self.const = const
        return

    @property
    def property_type(self) -> SettingType:
        return super().property_type

    @property
    def service_key(self) -> ServiceID:
        return super().service_key

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default

    def get_raw_value(self) -> int:
        default = self._default
        internal_value: int = SettingsLowLevel.get_setting_int(self.service_key,
                                                               default)
        # MY_LOGGER.debug(f'setting_id {self.setting_id} setting: {self.dep_setting_id} '
        #                     f'internal_value: {internal_value}')
        return internal_value

    def get_value(self) -> int | float:
        internal_value: int = self.get_raw_value()
        internal_value = min(internal_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: int | float = internal_value / self.internal_scale_factor
        if self.is_integer:
            tts_value: int = int(round(tts_value))
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'tts_value: {tts_value} int: {self.is_integer} '
                            f'scale: {self.internal_scale_factor}')
        return tts_value

    def scale_value(self, raw_value: int) -> float:
        value: float = float(raw_value) / float(self.internal_scale_factor)
        return value

    def get_value_from(self, raw_value: int,
                       convert: ConvertType = ConvertType.NONE,
                       is_integer: bool = False) -> int | float:
        """
        Returns the scaled value using the given raw value

        :param raw_value: Integral value, same as what is stored in settings.xml
                          The value returned value is scaled according to the
                          internal_scale_factor
        :param convert: If True, then the scaled value is converted to an int or
                        float, depending upon is_integer
        :param is_integer:
        :return:
        """
        # internal_value: int = self.get_raw_value()
        internal_value = min(raw_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: float = self.scale_value(internal_value)
        if convert == ConvertType.PERCENT and self.is_decibels:
            tts_value = 100.0 * (10 ** (tts_value / 20.0))
        elif convert == ConvertType.DECIBELS and not self.is_decibels:
            tts_value = 10.0 * math.log10(float(tts_value) / 100.0)
        if is_integer:
            return int(round(tts_value))
        return tts_value

    def set_value(self, value: int | float) -> None:
        if not self.const:
            internal_value: int = int(value * self.internal_scale_factor)
            internal_value = min(internal_value, self.maximum)
            internal_value = max(internal_value, self.minimum)
            SettingsLowLevel.set_setting_int(self.service_key, internal_value)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'in_value: {value} internal_value: {internal_value}')
        return

    def validate(self, value: int | None) -> bool:
        internal_value: int = self.get_raw_value()
        return internal_value in range(self.minimum, self.maximum)

    def as_percent(self) -> int | float:
        """
        Converts the value from decibels to percent.

        :return:
        """
        if not self.is_decibels:
            return self.get_value()

        internal_value: int = self.get_raw_value()
        internal_value = min(internal_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: int | float = internal_value / self.internal_scale_factor
        result = 100 * (10 ** (tts_value / 20.0))
        if self.is_integer:
            result = int(round(result))
        #  MY_LOGGER.debug(f'raw_value: {internal_value} result: {result}')
        return result

    def as_decibels(self) -> int | float:
        if self.is_decibels:
            return self.get_value()

        internal_value: int = self.get_raw_value()
        internal_value = min(internal_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: float | int = internal_value * self.internal_scale_factor
        result: float = 10.0 * math.log10(float(tts_value) / 100.0)
        return result

    def get_tts_values(self) -> UIValues:
        return self.get_values(convert=ConvertType.NONE, is_integer=self.is_integer)

    def get_values(self, convert: ConvertType = ConvertType.NONE,
                   is_integer: bool = False) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, current_value, minimum_increment,
                 values_are_int: bool)
        """
        result: UIValues
        result = UIValues(minimum=self.get_value_from(self.minimum, convert=convert,
                                                      is_integer=is_integer),
                          maximum=self.get_value_from(self.maximum, convert=convert,
                                                      is_integer=is_integer),
                          default=self.get_value_from(self.default,
                                                      convert=convert,
                                                      is_integer=is_integer),
                          current=self.get_value_from(self.get_raw_value(),
                                                      convert=convert,
                                                      is_integer=is_integer),
                          # increment=self.get_value_from(self.increment,
                          #                              convert=convert,
                          #                              is_integer=is_integer),
                          increment=self.scale_value(self.increment),
                          is_integer=is_integer)
        if MY_LOGGER.isEnabledFor(DEBUG_V):
            MY_LOGGER.debug_v(f'raw_value: {self.get_raw_value()} convert: {convert} '
                              f' integer: {is_integer}  {result} inc: {self.increment}')

        return result

    def __repr__(self) -> str:
        return f'service: {self.service_key}'

    def adjust(self, positive_increment: bool) -> float | int:
        """
        Increases/decreases the current value by one unit (increment).
        :param positive_increment: If True, then add one increment to value,
               else, subtract one increment
        :return: value after the increment (same as using get_value())
        """
        if self.const:
            return self.get_value()

        increment: int = self.increment
        if not positive_increment:
            increment = - increment
        new_raw_value: int = self.get_raw_value() + increment
        new_value: float | int = self.get_value_from(new_raw_value,
                                                     convert=ConvertType.NONE,
                                                     is_integer=self.is_integer)
        if MY_LOGGER.isEnabledFor(DEBUG):
            current = self.get_value_from(self.get_raw_value(),
                                          convert=ConvertType.NONE,
                                          is_integer=self.is_integer)
            MY_LOGGER.debug(f'increment: {self.increment} new_raw_value: {new_raw_value} '
                            f'new_value: {new_value} current: {current}')
        self.set_value(new_value)
        return self.get_value()   # Handles range checking


class NumericValidator(BaseNumericValidator):

    def __init__(self, service_key: ServiceID,
                 minimum: int | float, maximum: int | float,
                 default: int | float | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 increment: int | float = 0.0,
                 const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        self._service_key: ServiceID = service_key
        super().__init__(service_key=service_key,
                         minimum=minimum,
                         maximum=maximum,
                         default=default,
                         is_decibels=is_decibels,
                         is_integer=is_integer,
                         increment=increment,
                         const=False,
                         define_setting=define_setting,
                         service_status=service_status,
                         persist=persist)
        self.tts_validator: TTSNumericValidator | None = None
        if const:
            self.set_value(default)
            super().const = const
            self.const = const
        return

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default

    def _get_value(self) -> int | float:
        if self.const:
            return self.const
        if self.tts_validator is None:
            self.tts_validator: IValidator = self.get_tts_validator()
        self.tts_validator: TTSNumericValidator
        value: int | float
        if self.is_decibels:
            value = self.tts_validator.as_decibels()
        else:
            value = self.tts_validator.as_percent()
        return value

    def get_value(self) -> int | float:
        value: int | float = self._get_value()
        value = min(value, self.maximum)
        value = max(value, self.minimum)
        if self.is_integer:
            value = int(round(value))
        return value

    def get_value_from(self, raw_value: int) -> int | float:
        if self.const:
            return self.get_value()

        if self.tts_validator is None:
            self.tts_validator: IValidator = self.get_tts_validator()
        self.tts_validator: TTSNumericValidator
        # internal_value: int = self.get_raw_value()
        internal_value = min(raw_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: int | float = internal_value / self.tts_validator.internal_scale_factor
        if self.is_integer:
            return int(round(tts_value))
        return tts_value

    def set_value(self, value: int | float) -> None:
        if self.const:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug('const_value:, set ignored')
            return

        adj_value: int | float = min(value, self.maximum)
        adj_value = max(adj_value, self.minimum)
        if self.tts_validator is None:
            self.tts_validator: IValidator = self.get_tts_validator()
        self.tts_validator: TTSNumericValidator
        if self.tts_validator.is_decibels:
            adj_value = self.to_decibels(adj_value)
        else:
            adj_value = self.to_percent(adj_value)
        self.tts_validator.set_value(adj_value)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'orig_value: {value} adj_value: {adj_value}')
        return

    def validate(self, value: int | None) -> bool:
        value: int | float = self._get_value()
        return value in range(self.minimum, self.maximum)

    def as_percent(self) -> int | float:
        """
        Converts the value from decibels to percent.

        :return:
        """
        if not self.is_decibels:
            return self.get_value()

        value: int | float = self.get_value()
        result = 100 * (10 ** (value / 20.0))
        if self.is_integer:
            return int(round(result))
        return result

    def as_decibels(self) -> int | float:
        if self.is_decibels:
            return self.get_value()

        value: int | float = self.get_value()
        result: float = 10.0 * math.log10(float(value) / 100.0)
        return result

    def get_values(self) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, default_value, current_value,
                 minimum_increment, is_integer: bool)
        """
        result: UIValues
        result = UIValues(minimum=self.get_value_from(self.minimum),
                          maximum=self.get_value_from(self.maximum),
                          default=self.get_value_from(self.default),
                          current=self.get_value(),
                          increment=self.get_value_from(self.increment),
                          is_integer=self.is_integer)
        return result

    def get_tts_values(self) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, current_value, minimum_increment,
                 values_are_int: bool)
        """
        if self.tts_validator is None:
            self.tts_validator: IValidator = self.get_tts_validator()
        self.tts_validator: TTSNumericValidator
        convert: ConvertType = ConvertType.DECIBELS
        if not self.is_decibels:
            convert = ConvertType.PERCENT
        return self.tts_validator.get_values(convert=convert,
                                             is_integer=self.is_integer)

    def __repr__(self) -> str:
        result: str = ''
        if hasattr(self, 'service_key'):
            result = f'{result} service_key: {self.service_key}'
        if hasattr(self, 'maximum'):
            result = f'{result} service_key: {self.service_key}'
        if hasattr(self, 'is_decibels'):
            result = f'{result} is_decibels: {self.is_decibels}'
        return result

class IntValidator(Validator):

    def __init__(self, service_key: ServiceID,
                 min_value: int, max_value: int, default: int,
                 step: int, scale_internal_to_external: int = 1,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        super().__init__(service_key, property_type=SettingType.INTEGER_TYPE,
                         define_setting=define_setting,
                         service_status=service_status,
                         persist=persist)
        self._service_key: ServiceID = service_key
        self.min_value: int = min_value
        self.max_value: int = max_value
        self._default = default
        self.step: int = step
        self.scale_internal_to_external: int = scale_internal_to_external

        return

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    def get_tts_value(self, default: int | None = None) -> bool | int | float | str:
        if default is None:
            default = self._default

        internal_value: int = SettingsLowLevel.get_setting_int(self.service_key,
                                                               default)
        tts_val: IValidator | IntValidator
        tts_val = self.get_tts_validator()

        value: int = internal_value * tts_val.scale_internal_to_external
        value = min(value, tts_val.max_value)
        value = max(value, tts_val.min_value)
        return int(int(round(value)))

    def set_tts_value(self, value: int | float) -> None:
        tts_val: IValidator | IntValidator
        tts_val = self.get_tts_validator()

        value = min(value, tts_val.max_value)
        value = max(value, tts_val.min_value)
        internal_value: int = value * tts_val.scale_internal_to_external
        SettingsLowLevel.set_setting_int(self.service_key, internal_value)
        return

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> int:
        pass

    def getInternalValue(self) -> int:
        pass

    def setInternalValue(self, value: int) -> None:
        pass

    def getLabel(self) -> str:
        pass

    def getUnits(self) -> str:
        pass

    def validate(self, value: int | None) -> bool:
        internal_value: int = SettingsLowLevel.get_setting_int(self.service_key)
        if value is None:
            value: int = internal_value * self.scale_internal_to_external
        valid: bool = value > self.max_value
        valid = valid and (value < self.min_value)
        return valid

    def preValidate(self, ui_value: int) -> bool:
        pass

    def get_min_value(self) -> int:
        return self.min_value

    def get_max_value(self) -> int:
        return self.max_value


class StringValidator(IStringValidator):
    """
    Defines a Validator for String properties. The validator
    can be used for values which are string constants, one of a list
    of pre-defined values, any string of a specific length range or
    some combination of these values.
    """

    def __init__(self, service_key: ServiceID,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default: str = None,
                 allow_default: bool = True,
                 const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType | None = StatusType.OK,
                 persist: bool = True) -> None:
        """
        Defines the values which a property of the given service_key can
        be.
        :param service_key: ID of the service property
        :param allowed_values: List of allowed values. Can be an empty list
               indicating that max/min length and default settings will
               determine what the legal values are
        :param min_length: Minimum character length of a valid value
        :param max_length: Maximum character length of a valid value
        :param default: Defines a default value, which can be different
               from allowed_values. A value of None is allowed
        :param allow_default: If True, then the default parameter
               can be used, otherwise, ignore the default parameter
        :param const: If True, then the value can not be changed
        """
        super().__init__(service_key,
                         allowed_values, min_length,
                         max_length, default, allow_default,
                         const)
        self._service_key: ServiceID = service_key
        self.allowed_values: List[AllowedValue] = []
        self._default: str = default
        self._allow_default: bool = allow_default
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()

        """
        TODO: DISABLED allowed /is_available checking. For this to work properly
              1) It must be done dynamically on each call
              2) It must take into account if this service (service_key) is 
                 available/usable. 
              3) It must take into account if each choice (allowed_value) that is 
                 a SERVICE (player, engine, etc.) is available.
              4) For choices that are not a SERVICE but a setting for a service,
                 then it is allowed if the underlying service is available
              5) To pull 4 off, the ssetting id must include the fully qualified
                ServiceID for the setting
              6) Note that tts.tts is not a service, but perhaps a quasi-one. 
                 tts.tts.current_engine is a setting that contains a service value
                 also, all of the choices for tts.tts.current_engine are services.
        For is_available to work it must have fully 
              qualified service_keys. Here, allowed has simple ids (ex. player_ids).
        
        We may be choosing which player to use for an engine. In this case if 
        the engine is not available, then there are no viable players. However,
        if the engine is available, then we only want to choose from the players
        which are available. 
        
        
        """
        for p in allowed_values:
            p: str
            #  allowed: bool = SettingsMap.is_available(service_key, force=True)
            allowed: bool = True  # Hack
            allowed_value: AllowedValue = AllowedValue(p, allowed)
            self.allowed_values.append(allowed_value)
        if min_length is None:
            min_length = 0
        if max_length is None:
            max_length = 4096
        self.min_value: int = min_length
        self.max_value: int = max_length
        if not self._allow_default:
            default = None
        self._default: str = default
        return

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=self._property_type,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def __repr__(self) -> str:
        result: str = ''
        if hasattr(self, 'service_key'):
            result = f'{result} service_key: {self.service_key}'
        if hasattr(self, 'allowed_values'):
            result = f'{result} allowed: {self.allowed_values}'
        if hasattr(self, 'property_type'):
            result = f'{result} property_type: {self.property_type}'
        if hasattr(self, '_allow_default') and hasattr(self, '_default'):
            result = (f'{result} allow_default: {self._allow_default} '
                      f'default: {self._default}')
        return result

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    @property
    def property_type(self) -> SettingType:
        return super().property_type

    def get_tts_value(self, default: str | None = None) -> str | None:
        """
        Gets the value of a setting for the service identified by the constructor's
        setting_id argument.

        TODO: rename the method to 'get_value' unless a good reason is found
              not to.
        :param default:  Default value to use if no value is found. If missing,
                         the default parameter from the constructor will be used.
        :return:
        """
        valid: bool = True
        if self._allow_default:
            if default is None:
                default = self._default
        else:
            default = None
        value: str | None
        value = SettingsLowLevel.get_setting_str(self.service_key,
                                                 ignore_cache=False,
                                                 default=default)
        if value is None:
            return value
        allowed_value: AllowedValue | None = self.get_allowed_value(value)
        if allowed_value is not None:
            if not allowed_value.enabled:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'{value} is NOT enabled.')
                valid = False
                value = default

        if valid and not (self.min_value <= len(value) <= self.max_value):
            valid = False
            value = default

        return value

    def set_tts_value(self, value: str) -> None:
        valid: bool = True
        internal_value: str = value
        allowed: bool = True
        allowed_value: AllowedValue | None = self.get_allowed_value(value)
        if allowed_value is not None:
            allowed = allowed_value.enabled
        if not allowed:
            value = False
        if valid and len(internal_value) < self.min_value:
            valid = False
        if valid and len(internal_value) > self.max_value:
            valid = False

        if not valid:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'INVALID setting {self.service_key.short_key} '
                                f'value: {value} '
                                f'using {self.default} instead.')
            internal_value = self.default
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'setting {self.service_key.short_key} '
                            f'value: {value} ')
        SettingsLowLevel.set_setting_str(self.service_key, internal_value)

    @property
    def default(self) -> str | None:
        if not self._allow_default:
            return None
        allowed: bool = self.is_value_valid(self._default)
        default: str | None = None
        if allowed:
            default = self._default
        return default

    def get_allowed_values(self, enabled: bool | None = None) -> List[AllowedValue]:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. For example, while an engine
        may support PlayerMode.SLAVE_FILE an already chosen player may not,
        therefore blocking you from changing the PlayerMode

        :param enabled: If specified, then only return values which have the
                 enabled field == enabled param
        :return: A list of AllowedValues for every
                 supported value. Those settings which are in conflict with
                 a current setting will be marked disabled (False)
        Note that the supported values are in the order specified in settings_<service>.
        The assumption is that they are in the preferred order of that service.
        """
        allowed: List[AllowedValue] = []
        for setting in self.allowed_values:
            if enabled is None or setting.enabled == enabled:
                allowed.append(setting)
            # Check with each allowed player to determine if setting is
        return allowed

    def get_allowed_value(self, value: str) -> AllowedValue | None:
        for p in self.allowed_values:
            if p.value == value:
                return p

    def setUIValue(self, ui_value: str) -> None:
        pass

    def getUIValue(self) -> str:
        pass

    def getInternalValue(self) -> str:
        pass

    def setInternalValue(self, value: str) -> None:
        pass

    def getLabel(self) -> str:
        pass

    def getUnits(self) -> str:
        pass

    def validate(self, value: str | AllowedValue | None,
                 debug: bool = False) -> Tuple[bool, str]:
        valid: bool = True
        internal_value: str = SettingsLowLevel.get_setting_str(self.service_key,
                                                               ignore_cache=False,
                                                               default=None)
        if debug:
            MY_LOGGER.debug(f'{self.service_key} value: {value} '
                            f'internal_value: {internal_value}')
        if value is None:
            value = internal_value
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            found_value: AllowedValue = self.get_allowed_value(value)
            if found_value is None or not found_value.enabled:
                valid = False

        if debug:
            MY_LOGGER.debug(f'value: {value} valid: {valid} ')
        if valid and len(value) < self.min_value:
            valid = False
        if valid and len(value) > self.max_value:
            valid = False
        if debug:
            MY_LOGGER.debug(f'valid: {valid} len(value): {len(value)} '
                            f'min: {self.min_value} max: {self.max_value}')
            MY_LOGGER.debug(f'allowed values: {self.allowed_values}')

        return valid, value

    def is_value_valid(self, value: str | None) -> bool:
        for allowed_value in self.get_allowed_values():
            allowed_value: AllowedValue
            if value == allowed_value.value and allowed_value.enabled:
                return True
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'INVALID value: {value}')
        return False

    def preValidate(self, ui_value: str) -> Tuple[bool, str]:
        pass


'''
class EnumValidator(Validator):

    # Probably won't work as is, needs generics
    def __init__(self, service_key: ServiceID,
                 min_value: enum.Enum, max_value: enum.Enum,
                 default: enum.Enum = None) -> None:
        super().__init__(service_key)
        self._service_key: ServiceID = service_key
        self.current_value: enum.Enum = default
        self.min_value: enum.Enum = min_value
        self.max_value: enum.Enum = max_value
        self._default: enum.Enum = default
        return

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    def get_tts_value(self) -> enum.Enum:
        str_value: str = SettingsLowLevel.get_setting_str(self.service_key,
                                                          ignore_cache=False,
                                                          default=self._default.name)
        self.current_value = enum.Enum[str_value]
        return self.current_value

    def set_tts_value(self, value: enum.Enum) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.service_key, self.current_value.name)

    @property
    def default(self):
        return self._default

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> int:
        pass

    def getInternalValue(self) -> int | str:
        return self.current_value.name

    def setInternalValue(self, internalValue: int | str) -> None:
        pass

    def validate(self, value: enum.Enum | None) -> Tuple[bool, Any]:
        pass

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        pass
'''

'''
class ConstraintsValidator(Validator):

    def __init__(self, service_key: ServiceID,
                 property_type: SettingType,
                 constraints: Constraints | IConstraints | None,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        super().__init__(service_key, property_type,
                         define_setting=define_setting,
                         service_status=service_status,
                         persist=persist)
        self.constraints: Constraints | IConstraints = constraints
        self._tts_line_value: float | int = constraints.tts_line_value

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> str:
        pass

    def get_tts_values(self, default_value: int | float | str = None) \
            -> Tuple[int | float | str, int | float | str, int | float | str,
                     int | float | str]:
        """

        :param default_value:
        :return: current_value, min_value, default_value, max_value
        """
        clz = type(self)
        if default_value is None:
            default_value = self._default

        tts_val: IValidator | ConstraintsValidator = self.get_tts_validator()
        tts_constraints: IConstraints = tts_val.get_constraints()
        current_value: int | float = tts_constraints.currentValue(self.service_key)
        is_valid, _ = self.validate(current_value)
        if not is_valid:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'Invalid value for {self.service_key} '
                                f'Replaced with closest valid value')

        min_value: float | int | str
        default_value: float | int | str
        max_value: float | int | str
        min_value = tts_constraints.minimum
        default_value = tts_constraints.default
        max_value = tts_constraints.maximum

        if tts_constraints.integer:
            current_value = int(round(current_value))
            min_value = int(round(min_value))
            default_value = int(round(default_value))
            max_value = int(round(max_value))
        else:
            current_value = float(current_value)
            min_value = float(min_value)
            default_value = float(default_value)
            max_value = float(max_value)

        return current_value, min_value, default_value, max_value

    def set_tts_value(self, value: int | float | str) -> None:
        tts_val: IValidator | ConstraintsValidator = self.get_tts_validator()
        tts_constraints: IConstraints = tts_val.get_constraints()
        tts_constraints.setSetting(value, self.service_key)

    def get_impl_value(self,
                       setting_service_id: str | None = None,
                       as_decibels: bool | None = None,
                       limit: bool | None = None) -> int | float | str:
        """
            Translates the 'TTS' value (used internally) to the implementation's
            scale (player or engine).

            :setting_service_id: The service (engine, player, etc.) to get
                this validator's property from.
            :as_decibels: Converts between decibel and percentage units.
                         True, convert to decibels
                         False, convert to percentage units (based on the scale
                         configured for this validator)
                         None, use decibels or percentage, as set by constructor
            :limit: Limits the returned value to the range configured for this
                    validator
            :return: Returns the current, scaled value of the Setting with this
            constraint's property name. Default values are used, as needed.
        """
        constraints: IConstraints = self.constraints
        tts_val: IValidator | ConstraintsValidator = self.get_tts_validator()
        tts_constraints: IConstraints = tts_val.get_constraints()

        tts_value, _, _, _ = self.get_tts_values(default_value=None,
                                                 )
        value: int | float | str
        # Translates from tts to self units
        value = tts_constraints.translate_value(constraints, tts_value,
                                                as_decibels=as_decibels)
        if tts_constraints.integer:
            return int(round(value))
        else:
            value = float(value)
        return value

    def set_impl_value(self, value: int | float | str) -> None:
        constraints: IConstraints = self.constraints
        constraints.setSetting(value, self.service_key)
        tts_val: IValidator | ConstraintsValidator = self.get_tts_validator()
        tts_constraints: IConstraints = tts_val.get_constraints()

        tts_value: int | float = self.get_tts_value()
        value: int | float | str
        # Translates from self to tts units
        value = constraints.translate_value(tts_constraints, tts_value)

    @property
    def tts_line_value(self) -> int | float:
        value: int | float
        value = self._tts_line_value
        if self.constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return value

    @property
    def integer(self) -> bool:
        return self.constraints.integer

    def validate(self, value: int | float | None) -> Tuple[bool, int | float]:
        constraints: IConstraints = self.constraints
        if value is None:
            value = SettingsLowLevel.get_setting_int(self.service_key)
        in_range: bool = False
        if value is not None:
            value = value * constraints.scale
            in_range = constraints.in_range(value)
        if constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return in_range, value

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        pass

    def get_constraints(self) -> IConstraints | Constraints:
        return self.constraints

    @property
    def default(self) -> int | str | float:
        value: float | int | str = self.constraints.default
        if self.constraints.integer:
            value = int(round(value))
        elif not isinstance(value, str):
            value = float(value)
        return value

    def get_min_value(self) -> int | float:
        value: int | float = self.constraints.minimum
        if self.constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return value

    def get_max_value(self) -> int | float:
        value: int | float = self.constraints.maximum
        if self.constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return value

    def get_default_value(self) -> int | float | str:
        value: float | int = self.constraints.default
        if self.constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return value
    '''


class BoolValidator(Validator):

    def __init__(self, service_key: ServiceID,
                 default: bool, const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType | None = StatusType.OK,
                 persist: bool = True) -> None:
        super().__init__(service_key, property_type=SettingType.BOOLEAN_TYPE,
                         default=default, const=const,
                         define_setting=define_setting,
                         service_status=service_status, persist=persist)
        self._service_key: ServiceID = service_key
        self._default: bool = default
        self.const: bool = False  # Force set_tts_value to persist in settings
        if const:
            self.set_tts_value(default)
            self.const = const

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    def get_tts_value(self) -> bool:
        value = SettingsLowLevel.get_setting_bool(self._service_key,
                                                  ignore_cache=False,
                                                  default=self._default)
        return value

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default
        return None

    def set_tts_value(self, value: bool) -> None:
        if not self.const:
            SettingsLowLevel.set_setting_bool(self.service_key, value)

    @property
    def default(self):
        return self._default

    def setUIValue(self, ui_value: bool) -> None:
        pass

    def getUIValue(self) -> str:
        pass

    def getInternalValue(self) -> bool:
        pass

    def setInternalValue(self, internalValue: bool) -> None:
        pass

    def validate(self, value: bool | None) -> Tuple[bool, bool]:
        pass

    def preValidate(self, ui_value: bool) -> Tuple[bool, bool]:
        pass


class GenderValidator(IGenderValidator):

    def __init__(self, service_key: ServiceID,
                 min_value: Genders, max_value: Genders,
                 default: Genders = Genders.ANY,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        self._service_key: ServiceID = service_key
        self.current_value: Genders = default
        self.min_value: Genders = min_value
        self.max_value: Genders = max_value
        self._default: Genders = default
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()
        return

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=SettingType.STRING_TYPE,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def get_tts_value(self) -> Genders:
        str_value: str = SettingsLowLevel.get_setting_str(self.service_key,
                                                          ignore_cache=False,
                                                          default=self._default.value)
        # Genders(Genders.MALE.value) works as well as Genders[Genders.MALE.name]
        self.current_value = Genders(str_value.lower())
        return self.current_value

    def set_tts_value(self, value: Genders) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self._service_key,
                                         self.current_value.name)

    def setUIValue(self, ui_value: str) -> None:
        # Use the enum's value: Genders.MALE.value() or 'male'
        self.set_tts_value(Genders(ui_value.lower()))

    def getUIValue(self) -> str:
        return self.get_tts_value().name

    def get_default_value(self) -> Genders | None:
        return self._default

    def getInternalValue(self) -> Genders:
        return self.get_tts_value()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError

    def validate(self, value: Genders | None) -> Tuple[bool, Any]:
        raise NotImplementedError

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError


class ChannelValidator(IChannelValidator):

    def __init__(self, service_key: ServiceID,
                 min_value: Channels, max_value: Channels,
                 default: Channels = Channels.NO_PREF,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        self._service_key: ServiceID = service_key
        self._property_type: SettingType = SettingType.STRING_TYPE
        self.current_value: Channels = default
        self.min_value: Channels = min_value
        self.max_value: Channels = max_value
        self._default: Channels = default
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()
        return

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    @property
    def property_type(self) -> SettingType:
        return SettingType.STRING_TYPE

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=self._property_type,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def get_tts_value(self) -> Channels:
        str_value: str = SettingsLowLevel.get_setting_str(self.service_key,
                                                          ignore_cache=False,
                                                          default=self._default.value)
        # Channels(Channels.MALE.value) works as well as Channels[Channels.MALE.name]
        try:
            self.current_value = Channels(str_value.lower())
        except ValueError:
            MY_LOGGER.debug(f'Invalid Channel value of {str_value}. Set to stereo.')
            self.current_value = Channels.STEREO
        return self.current_value

    def set_tts_value(self, value: Channels) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.service_key, self.current_value.name)

    def setUIValue(self, ui_value: str) -> None:
        # Use the enum's value: Channels.MALE.value() or 'male'
        self.set_tts_value(Channels(ui_value.lower()))

    def getUIValue(self) -> str:
        return self.get_tts_value().name

    def get_value(self) -> str:
        return self.getInternalValue()

    def getInternalValue(self) -> Channels:
        return self.get_tts_value()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError

    def validate(self, value: Channels | None) -> Tuple[bool, Any]:
        raise NotImplementedError

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError


class EngineValidator:
    """
    Validator for getting and setting engine ids from Settings.

    Enhancements include verifying if an engine is marked as non-functional.
    If an engine is non-functional, an Exception is thrown indicating that a new
    engine needs to be picked.
    """

    def __init__(self) -> None:
        return

    @property
    def property_type(self) -> SettingType:
        return SettingType.STRING_TYPE

    def get_service_key(self) -> ServiceID:
        """
        Gets the current engine_id. If the engine is non-functional, then
        a ServiceUnavailable is thrown containing the failing setting_id
        and the reason.
        """

        service_key: ServiceID = SettingsLowLevel.get_engine_id_ll(ignore_cache=False)
        #  MY_LOGGER.debug(f'engine_id from SettingsLowLevel: {service_key}')
        if SettingsMap.is_available(service_key):
            #  MY_LOGGER.debug(f'is_available: {service_key}')
            return service_key
        raise ServiceUnavailable(service_key=service_key, reason=Status.UNKNOWN,
                                 active=True)

    def set_service_key(self, engine_key: ServiceID) -> None:
        """
        Sets the current engine_id. If the engine is non-functional, then
        a ServiceUnavailable is thrown containing the failing setting_id
        and the reason.
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'TRACE: engine_key: {engine_key} {type(engine_key)}' 
                            f' service_id: {engine_key.service_id} '
                            f' type: {type(engine_key.service_id)} ')

        if not SettingsMap.is_available(engine_key):
            raise ServiceUnavailable(service_key=engine_key, reason=Status.UNKNOWN,
                                     active=True)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'is_available: {engine_key}')
        SettingsLowLevel.set_engine(engine_key)


class DependencyValidator:  # (IDependencyValidator):
    """
        Used when one service has a dependency on another service. Example:
        engines frequently depend upon a player. If a player is not available
        then it should not be considered for use. The validator will
        dynimically verify that settings are valid and act accordingly.
    """

    def __init__(self, service_key: ServiceID,
                 dep_svc_type: ServiceType,
                 dep_srvc_ids: List[str]) -> None:
        """
        Creates a validator for a service (ex. an engine) which requires another
        service (ex. a player). This is created by the user of the service
        (ex: eSpeak) and populated with the service type it needs (player) as
        well as a list of the players which it will accept (internal, mpv, etc.).

        To help determine which player to choose for the engine, each
        candidate player is examined. To get more data about a player (such is
        it broken) a service_key is created for the player.

        :param service_key: Identifies the service type and service id
                            ex engine, google
        :param dep_svc_type: Type that the service_type depends on:
                                       ex: player
        :param dep_srvc_ids:  service ids that are instances of the
                              dependent_service_type: ex mplayer, sfx
        """
        # super().__init__(service_key,
        #                  dep_svc_type, dep_srvc_ids)
        self._service_key: ServiceID = service_key
        # create a Service.Key for the dependency so that it's health, etc.
        # can be examined:
        # Ex. Engine google_tts wants to pick the best player from a list of
        # players. dep_svc_type is 'player' and each dep_srvc_id is the player id
        # to look up. For some things (like looking up the player's health)
        # this is all that is needed. For checking other things specific
        # settings for the player can be looked up.

        self.allowed_values: List[AllowedValue] = []
        for dep_serv_id in dep_srvc_ids:
            dep_serv_id: str
            dep_service_key: ServiceID = ServiceID(dep_svc_type, dep_serv_id)
            allowed: bool = SettingsMap.is_available(dep_service_key)
            allowed_value: AllowedValue = AllowedValue(dep_serv_id, allowed,
                                                       dep_service_key)
            self.allowed_values.append(allowed_value)
        return

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

    @property
    def property_type(self) -> SettingType:
        return SettingType.STRING_TYPE

    def get_value(self) -> str | None:
        """
        Retrieves the value from Settings, validates that it is valid using the
        enabled AllowedValues. If no match found, then return first enabled
        AllowedValue
        :return:
        """
        valid: bool = True
        value: str | None
        value = SettingsLowLevel.get_setting_str(self.service_key,
                                                 ignore_cache=False)
        if value is None:
            return value
        allowed_value: AllowedValue | None = self.get_allowed_value(value)
        if allowed_value is not None:
            if not allowed_value.enabled:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'{value} is NOT enabled.')
                valid = False
        return value

    def set_value(self, value: str) -> None:
        valid: bool = True
        internal_value: str = value
        allowed: bool = True
        allowed_value: AllowedValue | None = self.get_allowed_value(value)
        if allowed_value is not None:
            valid = allowed_value.enabled   # Only pick enabled values
        if not valid:
            raise ValueError(f'INVALID setting {self.service_key} '
                             f'value: {value}.')
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'setting {self.service_key} value: {value} ')
        SettingsLowLevel.set_setting_str(self.service_key, internal_value)

    def get_allowed_values(self, enabled: bool | None = None) -> List[AllowedValue]:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. For example, while an engine
        may support PlayerMode.SLAVE_FILE an already chosen player may not,
        therefore blocking you from changing the PlayerMode

        :param enabled: If specified, then only return values which have the
                 enabled field == enabled param
        :return: A list of AllowedValues for every
                 supported value. Those settings which are in conflict with
                 a current setting will be marked disabled (False)
        Note that the supported values are in the order specified in settings_<service>.
        The assumption is that they are in the preferred order of that service.
        """
        allowed: List[AllowedValue] = []
        for setting in self.allowed_values:
            if enabled is None or setting.enabled == enabled:
                allowed.append(setting)
            # Check with each allowed player to determine if setting is
        return allowed

    def get_allowed_value(self, value: str) -> AllowedValue | None:
        """
        finds the given value in the list of AllowedValues

        :param value:
        :return: Fould AllowedValue, or None
        """
        for p in self.allowed_values:
            if p.value == value:
                return p

    def validate(self, value: str | AllowedValue | None,
                 debug: bool = False) -> Tuple[bool, str]:
        valid: bool = True
        if not isinstance(value, AllowedValue):
            raise ValueError(f'Expected an Allowed value not {value}')
        allowed_value: AllowedValue = value
        dep_svc_key: ServiceID = allowed_value._service_key
        internal_value: str = SettingsLowLevel.get_setting_str(dep_svc_key,
                                                               ignore_cache=False,
                                                               default=None)
        if debug:
            MY_LOGGER.debug(f'{dep_svc_key} value: {value} '
                            f'internal_value: {internal_value}')
        if value is None:
            value = internal_value
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            found_value: AllowedValue = self.get_allowed_value(value)
            if found_value is None or not found_value.enabled:
                valid = False
        return valid, value

    def is_value_valid(self, value: str | None) -> bool:
        for allowed_value in self.get_allowed_values():
            allowed_value: AllowedValue
            if value == allowed_value.value and allowed_value.enabled:
                return True
        return False

    def preValidate(self, ui_value: str) -> Tuple[bool, str]:
        pass


class SimpleIntValidator(ISimpleValidator):
    def __init__(self, service_key: ServiceID, value: int,
                 const: bool = True,
                 define_setting: bool = True,
                 service_status: StatusType = StatusType.OK,
                 persist: bool = True) -> None:
        super().__init__(service_key=service_key,
                         property_type=SettingType.INTEGER_TYPE,
                         const=const)
        self._service_key: ServiceID = service_key
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} value: {value} const: {const}')
        self._value: int = value
        self._const: bool = const
        self._const_value: int | None = None
        if const:
            self._const_value = value
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=self._property_type,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def get_value(self) -> int:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} value: {self._value}')
        return self._value

    def get_const_value(self) -> int:
        if self._const:
            return self._const_value

    def is_const(self) -> bool:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} const: {self._const}')
        return self._const

    @property
    def service_key(self) -> ServiceID:
        return self._service_key


class SimpleStringValidator(ISimpleValidator):
    def __init__(self, service_key: ServiceID,
                 value: str,
                 const: bool = True,
                 define_setting: bool = True,
                 service_status: StatusType | None = StatusType.OK,
                 persist: bool = True) -> None:
        super().__init__(service_key=service_key,
                         property_type=SettingType.STRING_TYPE,
                         const=const)
        self._service_key: ServiceID = service_key
        self._value: str = value
        self._const: bool = const
        self._const_value: str | None = None
        if const:
            self._const_value = value
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} value: {value} const: {const}')
        self._define_setting: bool = define_setting
        self._service_status: StatusType = service_status
        self._persist: bool = persist
        if self._define_setting:
            self.define_setting()

    @property
    def property_type(self) -> SettingType:
        return super().property_type

    def define_setting(self) -> None:
        SettingsMap.define_setting(service_id=self._service_key,
                                   setting_type=self._property_type,
                                   service_status=self._service_status,
                                   validator=self,
                                   persist=self._persist)

    def get_value(self) -> str:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} value: {self._value} '
                            f'const: {self._const}')
        return self._value

    def get_const_value(self) -> str:
        if self._const:
            return self._const_value

    def is_const(self) -> bool:
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self._service_key} value: {self._value} const: '
                            f'{self._const}')
        return self._const

    @property
    def service_key(self) -> ServiceID:
        return self._service_key
