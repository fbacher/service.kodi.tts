# coding=utf-8
import enum

from backends.settings.constraints import Constraints
from backends.settings.i_constraints import IConstraints
from backends.settings.i_validators import IGenderValidator, IStringValidator, IValidator
from common.logger import BasicLogger
from common.setting_constants import Genders
from common.settings_low_level import SettingsLowLevel
from common.typing import *

module_logger = BasicLogger.get_module_logger(module_path=__file__)


class Validator(IValidator):
    def __init__(self, setting_id: str, engine_id: str) -> None:
        self._default = None
        super().__init__(setting_id, engine_id)
        self.depends_on_setting_id = None
        self.depends_on_service_id = None

    def depends_on(self, setting_id: str, service_id: str) -> None:
        self.depends_on_setting_id = setting_id,
        self.depends_on_service_id = service_id


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

    def getValue(self, default: int | None = None) -> bool | int | float | str:
        if default is None:
            default = self._default
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id,
                                                               self.service_id,
                                                               default)
        value: int = internal_value * self.scale_internal_to_external
        value = min(value, self.max_value)
        value = max(value, self.min_value)
        return int(round(value))

    def setValue(self, value: int | float) -> None:
        value = min(value, self.max_value)
        value = max(value, self.min_value)
        internal_value: int = value * self.scale_internal_to_external
        SettingsLowLevel.set_setting_int(self.setting_id, internal_value, self.service_id)
        return

    def setUIValue(self, ui_value:int) -> None:
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

    def get_default_value(self) -> int:
        return self._default


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

    def getValue(self, default : str | None = None) -> str:
        valid: bool = True
        if default is None:
            default = self._default
        internal_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                               self.service_id,
                                                               ignore_cache=False,
                                                               default=default)
        if internal_value is None:
            internal_value = self._default
        return internal_value

        module_logger.debug(f'internal: {internal_value}')
        if ((self.allowed_values is None) or (internal_value is None)
                and (len(self.allowed_values) > 0)):
            valid = False
            module_logger.debug(f'internal_value or allowed_values is None')
        if valid and internal_value not in self.allowed_values:
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

    def setValue(self, value: str) -> None:
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

    def setUIValue(self, ui_value:str) -> None:
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

    def getValue(self) -> enum.Enum:
        str_value: str = SettingsLowLevel.get_setting_str(self.setting_id, self.service_id,
                                                          ignore_cache=False,
                                                          default=self._default.name)
        self.current_value = enum.Enum[str_value]
        return self.current_value

    def setValue(self, value: enum.Enum) -> None:
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
                 constraints: IConstraints) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.constraints: IConstraints = constraints

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> str:
        pass

    def getValue(self) -> int | float | str:
        constraints: IConstraints = self.constraints
        value: int | float = constraints.currentValue(self.service_id)
        return value

    def setValue(self, value: int | float | str) -> None:
        constraints: IConstraints = self.constraints
        constraints.setSetting(value, self.service_id)

    def validate(self, value: int | float | None) -> Tuple[bool, int | float]:
        constraints: IConstraints = self.constraints
        if value is None:
            value = SettingsLowLevel.get_setting_int(constraints.property_name,
                                                     self.service_id)
        in_range: bool = False
        if value is not None:
            value = value * constraints.scale
            in_range = constraints.in_range(value)
        return in_range, value

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        pass

    def get_constraints(self) -> IConstraints:
        return self.constraints

    @property
    def default_value(self) -> int | str | float:
        return self.constraints.default

    def get_min_value(self) -> int | float:
        return self.constraints.minimum

    def get_max_value(self) -> int | float:
        return self.constraints.maximum

    def get_default_value(self) -> int | float:
        return self.constraints.default



class BoolValidator(Validator):
    def __init__(self, setting_id: str, service_id: str,
                 default: bool) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self._default: bool = default

    def getValue(self) -> bool:
        value = SettingsLowLevel.get_setting_bool(self.setting_id, self.service_id,
                                                  ignore_cache=False,
                                                  default=self._default)
        return value

    def setValue(self, value: bool) -> None:
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

    def getValue(self) -> Genders:
        str_value: str = SettingsLowLevel.get_setting_str(self.setting_id, self.service_id,
                                                          ignore_cache=False,
                                                          default=self._default.value)
        # Genders(Genders.MALE.value) works as well as Genders[Genders.MALE.name]
        self.current_value = Genders(str_value.lower())
        return self.current_value

    def setValue(self, value: Genders) -> None:
        self.current_value = value
        SettingsLowLevel.set_setting_str(self.setting_id, self.current_value.name,
                                         self.service_id)

    def setUIValue(self, ui_value: str) -> None:
        # Use the enum's value: Genders.MALE.value() or 'male'
        self.setValue(Genders(ui_value.lower()))

    def getUIValue(self) -> str:
        return self.getValue().name

    def getInternalValue(self) -> Genders:
        return self.getValue()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError

    def validate(self, value: Genders | None) -> Tuple[bool, Any]:
        raise NotImplementedError

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError
