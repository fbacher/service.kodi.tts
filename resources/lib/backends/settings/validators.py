# coding=utf-8
from __future__ import annotations  # For union operator |

import enum
import math

from common import *

from backends.settings.constraints import Constraints
from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import (IChannelValidator, IGenderValidator,
                                            IStringValidator, IValidator, UIValues)
from backends.settings.service_types import Services
from backends.settings.settings_map import SettingsMap
from common.logger import BasicLogger
from common.setting_constants import Channels, Genders
from common.settings_low_level import SettingsLowLevel

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class ConvertType(enum.Enum):
    NONE = enum.auto()
    PERCENT = enum.auto()
    DECIBELS = enum.auto()


class Validator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 default: Any | None = None, const: bool = False) -> None:
        self._default = None
        super().__init__(setting_id, service_id)
        self.service_id = service_id
        self.setting_id = setting_id
        self.const: bool = const
        self.tts_validator: IValidator | None = None

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        return None

    def get_tts_validator(self) -> IValidator:
        if self.tts_validator is None:
            if self.service_id == Services.TTS_SERVICE:
                return self
        try:
            tts_val = SettingsMap.get_validator(Services.TTS_SERVICE,
                                                self.setting_id)
            self.tts_validator = tts_val
        except Exception:
            module_logger.exception('')
        return self.tts_validator


class BaseNumericValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 minimum: int, maximum: int,
                 default: int | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 increment: int | float = 0.0,
                 const: bool = False
                 ) -> None:
        super().__init__(setting_id, service_id, const=const)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.minimum: int = minimum
        self.maximum: int = maximum
        self._default = default
        self.is_decibels: bool = is_decibels
        self.is_integer = is_integer
        if increment is None or increment <= 0.0:
            increment = (maximum - minimum) / 20.0
        self._increment = increment
        self.const: bool = const
        return

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default_value

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
    def default_value(self) -> int:
        return self._default


class TTSNumericValidator(BaseNumericValidator):

    def __init__(self, setting_id: str,
                 minimum: int | float, maximum: int | float,
                 default: int | float | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 internal_scale_factor: int | float = 1,
                 increment: int | float = 0.0,
                 const: bool = False
                 ) -> None:
        super().__init__(setting_id=setting_id,
                         service_id=Services.TTS_SERVICE,
                         minimum=minimum,
                         maximum=maximum,
                         default=default,
                         is_decibels=is_decibels,
                         is_integer=is_integer,
                         increment=increment,
                         const=False)
        self.internal_scale_factor: int | float = internal_scale_factor
        if const:
            self.set_value(default)
            super().const = const
            self.const = const
        return

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default_value

    def get_raw_value(self) -> int:
        default = self._default
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id,
                                                               self.service_id,
                                                               default)
        # module_logger.debug(f'service_id {self.service_id} setting: {self.setting_id} '
        #                     f'internal_value: {internal_value}')
        return internal_value

    def get_value(self) -> int | float:
        internal_value: int = self.get_raw_value()
        internal_value = min(internal_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: int | float = internal_value / self.internal_scale_factor
        if self.is_integer:
            return int(round(tts_value))
        return tts_value

    def get_value_from(self, raw_value: int,
                       convert: ConvertType = ConvertType.NONE,
                       is_integer: bool = False) -> int | float:
        # internal_value: int = self.get_raw_value()
        internal_value = min(raw_value, self.maximum)
        internal_value = max(internal_value, self.minimum)
        tts_value: float = float(internal_value) / float(self.internal_scale_factor)
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
            SettingsLowLevel.set_setting_int(self.setting_id, internal_value,
                                             self.service_id)
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
        #  module_logger.debug(f'raw_value: {internal_value} result: {result}')
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
                          default=self.get_value_from(self.default_value,
                                                      convert=convert,
                                                      is_integer=is_integer),
                          current=self.get_value_from(self.get_raw_value(),
                                                      convert=convert,
                                                      is_integer=is_integer),
                          increment=self.get_value_from(self.increment,
                                                        convert=convert,
                                                        is_integer=is_integer),
                          is_integer=is_integer)
        # module_logger.debug(f'raw_value: {self.get_raw_value()}'
        #                     f' current: {result.current}')

        return result

    def __repr__(self) -> str:
        return (f'service: {self.service_id} setting: {self.setting_id} '
                f'val: {self.get_value()} db: {self.is_decibels}')

    def adjust(self, positive_increment: bool) -> float | int:
        """
        Increases/decreases the current value by one unit (increment).
        :param positive_increment: If True, then add one increment to value,
               else, subtract one increment
        :return: value after the increment (same as using get_value())
        """
        if self.const:
            return self.get_value()

        value: float | int = self.get_value_from(self.increment,
                                                 convert=ConvertType.NONE,
                                                 is_integer=self.is_integer)
        current = self.get_value_from(self.get_raw_value(),
                                      convert=ConvertType.NONE,
                                      is_integer=self.is_integer)
        if not positive_increment:
            value = -value
        current += value
        self.set_value(current)
        return self.get_value()   # Handles range checking


class NumericValidator(BaseNumericValidator):

    def __init__(self, setting_id: str, service_id: str,
                 minimum: int | float, maximum: int | float,
                 default: int | float | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 increment: int | float = 0.0,
                 const: bool = False
                 ) -> None:
        super().__init__(setting_id=setting_id,
                         service_id=service_id,
                         minimum=minimum,
                         maximum=maximum,
                         default=default,
                         is_decibels=is_decibels,
                         is_integer=is_integer,
                         increment=increment,
                         const=False)
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
            return self.default_value

    def _get_value(self) -> int | float:
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
            return

        value = min(value, self.maximum)
        value = max(value, self.minimum)
        if self.tts_validator is None:
            self.tts_validator: IValidator = self.get_tts_validator()
        self.tts_validator: TTSNumericValidator
        if self.tts_validator.is_decibels:
            value = self.to_decibels(value)
        else:
            value = self.to_percent(value)
        self.tts_validator.set_value(value)
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
                          default=self.get_value_from(self.default_value),
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
        return (f'service: {self.service_id} setting: {self.setting_id} '
                f'val: {self.get_value()} max: {self.maximum} db: {self.is_decibels}')


class IntValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: int, max_value: int, default: int,
                 step: int, scale_internal_to_external: int = 1) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.min_value: int = min_value
        self.max_value: int = max_value
        self._default = default
        self.step: int = step
        self.scale_internal_to_external: int = scale_internal_to_external
        return

    def get_tts_value(self, default: int | None = None,
                      setting_service_id: str = None) -> bool | int | float | str:
        if default is None:
            default = self._default
        if setting_service_id is None:
            setting_service_id = SettingsLowLevel.get_engine_id_ll()
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id,
                                                               setting_service_id,
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
        SettingsLowLevel.set_setting_int(self.setting_id, internal_value, self.service_id)
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
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id,
                                                               self.service_id)
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

    def __init__(self, setting_id: str, service_id: str,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default: str = None) -> None:
        super().__init__(setting_id, service_id, allowed_values, min_length,
                         max_length, default)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.allowed_values: List[str] = allowed_values
        if min_length is None:
            min_length = 0
        if max_length is None:
            max_length = 4096
        self.min_value: int = min_length
        self.max_value: int = max_length
        self._default: str = default
        return

    def get_tts_value(self, default: str | None = None,
                      setting_service_id: str = None) -> str:
        valid: bool = True
        if default is None:
            default = self._default
        if setting_service_id is None:
            setting_service_id = SettingsLowLevel.get_engine_id_ll()
        internal_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                               setting_service_id,
                                                               ignore_cache=False,
                                                               default=default)
        if internal_value is None:
            internal_value = self._default
            # module_logger.debug(f'using default player: {internal_value} for '
            #                     f'{setting_service_id} {self.setting_id}')
            return internal_value

        # module_logger.debug(f'internal: {internal_value}  for '
        #                     f'{setting_service_id} {self.setting_id}')
        if (self.allowed_values is None) or (internal_value is None):
            valid = False
            # module_logger.debug(f'internal_value or allowed_values is None')
        if (valid and (len(self.allowed_values) > 0)
                and (internal_value not in self.allowed_values)):
            valid = False
            module_logger.debug(f'internal not allowed value')
        if valid and len(internal_value) < self.min_value:
            valid = False
        if valid and len(internal_value) > self.max_value:
            valid = False
        if not valid:
            internal_value = self._default
        value: str = internal_value
        return value

    def set_tts_value(self, value: str) -> None:
        valid: bool = True
        internal_value: str = value
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            if internal_value not in self.allowed_values:
                valid = False
        if valid and len(internal_value) < self.min_value:
            valid = False
        if valid and len(internal_value) > self.max_value:
            valid = False
        if not valid:
            internal_value = self._default
        SettingsLowLevel.set_setting_str(self.setting_id, internal_value, self.service_id)

    @property
    def default_value(self) -> str:
        return self._default

    def get_allowed_values(self) -> List[str] | None:
        return self.allowed_values

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

    def validate(self, value: str | None) -> Tuple[bool, str]:
        valid: bool = True
        internal_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                               self.service_id,
                                                               ignore_cache=False,
                                                               default=None)
        if value is None:
            value = internal_value
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            if value not in self.allowed_values:
                valid = False
        if valid and len(value) < self.min_value:
            valid = False
        if valid and len(value) > self.max_value:
            valid = False

        return valid, value

    def preValidate(self, ui_value: str) -> Tuple[bool, str]:
        pass


class EnumValidator(Validator):

    # Probably won't work as is, needs generics
    def __init__(self, setting_id: str, service_id: str,
                 min_value: enum.Enum, max_value: enum.Enum,
                 default: enum.Enum = None) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.current_value: enum.Enum = default
        self.min_value: enum.Enum = min_value
        self.max_value: enum.Enum = max_value
        self._default: enum.Enum = default
        return

    def get_tts_value(self) -> enum.Enum:
        str_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                          self.service_id,
                                                          ignore_cache=False,
                                                          default=self._default.name)
        self.current_value = enum.Enum[str_value]
        return self.current_value

    def set_tts_value(self, value: enum.Enum) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.setting_id, self.current_value.name,
                                         self.service_id)

    @property
    def default_value(self):
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


class ConstraintsValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 constraints: Constraints | IConstraints | None) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        #   self.service_id: str = service_id
        self.constraints: Constraints | IConstraints = constraints
        self._tts_line_value: float | int = constraints.tts_line_value

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> str:
        pass

    def get_tts_values(self, default_value: int | float | str = None,
                       setting_service_id: str = None) \
            -> Tuple[int | float | str, int | float | str, int | float | str, \
                     int | float | str]:
        """

        :param default_value:
        :param setting_service_id:
        :return: current_value, min_value, default_value, max_value
        """
        clz = type(self)
        if default_value is None:
            default_value = self._default
        if setting_service_id is None:
            setting_service_id = SettingsLowLevel.get_engine_id_ll()

        tts_val: IValidator | ConstraintsValidator = self.get_tts_validator()
        tts_constraints: IConstraints = tts_val.get_constraints()
        current_value: int | float = tts_constraints.currentValue(setting_service_id)
        is_valid, _ = self.validate(current_value)
        if not is_valid:
            module_logger.debug(f'Invalid value for {self.setting_id} service: '
                                f'{Services.TTS_SERVICE} Replaced with closest valid '
                                f'value')

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
        tts_constraints.setSetting(value, self.service_id)

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
                                                 setting_service_id=setting_service_id)
        value: int | float | str
        # Translates from tts to self units
        value = tts_constraints.translate_value(constraints, tts_value,
                                                as_decibels=as_decibels,
                                                limit=limit)
        if tts_constraints.integer:
            return int(round(value))
        else:
            value = float(value)
        return value

    def set_impl_value(self, value: int | float | str) -> None:
        constraints: IConstraints = self.constraints
        constraints.setSetting(value, self.service_id)
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
            value = SettingsLowLevel.get_setting_int(constraints.property_name,
                                                     self.service_id)
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
    def default_value(self) -> int | str | float:
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

    '''
    def get_default_value(self) -> int | float | str:
        value: float | int = self.constraints.default
        if self.constraints.integer:
            value = int(round(value))
        else:
            value = float(value)
        return value
    '''


class BoolValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 default: bool, const: bool = False) -> None:
        super().__init__(setting_id, service_id, default=default, const=const)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self._default: bool = default
        self.const: bool = False  # Force set_tts_value to persist in settings
        if const:
            self.set_tts_value(default)
            self.const = const

    def get_tts_value(self) -> bool:
        value = SettingsLowLevel.get_setting_bool(self.setting_id, self.service_id,
                                                  ignore_cache=False,
                                                  default=self._default)
        return value

    def is_const(self) -> bool:
        return self.const

    def get_const_value(self) -> Any:
        if self.const:
            return self.default_value
        return None

    def set_tts_value(self, value: bool) -> None:
        if not self.const:
            SettingsLowLevel.set_setting_bool(self.setting_id, value, self.service_id)

    @property
    def default_value(self):
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

    def __init__(self, setting_id: str, service_id: str,
                 min_value: Genders, max_value: Genders,
                 default: Genders = Genders.UNKNOWN) -> None:
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.current_value: Genders = default
        self.min_value: Genders = min_value
        self.max_value: Genders = max_value
        self._default: Genders = default
        return

    def get_tts_value(self) -> Genders:
        str_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                          self.service_id,
                                                          ignore_cache=False,
                                                          default=self._default.value)
        # Genders(Genders.MALE.value) works as well as Genders[Genders.MALE.name]
        self.current_value = Genders(str_value.lower())
        return self.current_value

    def set_tts_value(self, value: Genders) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.setting_id, self.current_value.name,
                                         self.service_id)

    def setUIValue(self, ui_value: str) -> None:
        # Use the enum's value: Genders.MALE.value() or 'male'
        self.set_tts_value(Genders(ui_value.lower()))

    def getUIValue(self) -> str:
        return self.get_tts_value().name

    def getInternalValue(self) -> Genders:
        return self.get_tts_value()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError

    def validate(self, value: Genders | None) -> Tuple[bool, Any]:
        raise NotImplementedError

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError


class ChannelValidator(IChannelValidator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: Channels, max_value: Channels,
                 default: Channels = Channels.NO_PREF) -> None:
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.current_value: Channels = default
        self.min_value: Channels = min_value
        self.max_value: Channels = max_value
        self._default: Channels = default
        return

    def get_tts_value(self) -> Channels:
        str_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                          self.service_id,
                                                          ignore_cache=False,
                                                          default=self._default.value)
        # Channels(Channels.MALE.value) works as well as Channels[Channels.MALE.name]
        self.current_value = Channels(str_value.lower())
        return self.current_value

    def set_tts_value(self, value: Channels) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.setting_id, self.current_value.name,
                                         self.service_id)

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
