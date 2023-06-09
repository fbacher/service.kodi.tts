# coding=utf-8
import enum

from backends.settings.constraints import Constraints
from backends.settings.i_validators import IValidator, ValueType
from common.settings_low_level import SettingsLowLevel
from common.typing import *


class Validator(IValidator):
    def __init__(self, setting_id: str, engine_id: str) -> None:
        self._default_value = None
        super().__init__(setting_id, engine_id)


class IntValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: int, max_value: int, default_value: int,
                 step: int, scale_internal_to_external: int = 1) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.min_value: int = min_value
        self.max_value: int = max_value
        self._default_value = default_value
        self.step: int = step
        self.scale_internal_to_external: int = scale_internal_to_external
        return

    def getValue(self, default_value: int | None = None,
                value_type: ValueType = ValueType.VALUE) -> bool | int | float| str:
        if default_value is None:
            default_value = self.default_value
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id,
                                                               self.service_id,
                                                               default_value)
        value: int = internal_value * self.scale_internal_to_external
        value = min(value, self.max_value)
        value = max(value, self.min_value)
        return int(round(value))

    def setValue(self, value: int | float,
                 value_type: ValueType = ValueType.VALUE) -> None:
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

    def validate(self) -> Tuple[bool, int]:
        internal_value: int = SettingsLowLevel.get_setting_int(self.setting_id, self.service_id)
        value: int = internal_value * self.scale_internal_to_external
        valid: bool = value > self.max_value
        valid = valid and (value < self.min_value)
        return valid

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        pass


class StringValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default_value: str = None) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.allowed_values: List[str] = allowed_values
        if min_length is None:
            min_length = 0
        if max_length is None:
            max_length = 4096
        self.min_value: int = min_length
        self.max_value: int = max_length
        self._default_value: str = default_value
        return

    def getValue(self, default_value : str | None = None,
                 value_type: ValueType = ValueType.VALUE) -> str:
        valid: bool = True
        if default_value  is None:
            default_value = self.default_value
        internal_value: str = SettingsLowLevel.get_setting_str(self.setting_id,
                                                               self.service_id, default_value)
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            if internal_value not in self.allowed_values:
                valid = False
        if valid and len(internal_value) < self.min_value:
            valid = False
        if valid and len(internal_value) > self.max_value:
            valid = False
        if not valid:
            internal_value = self._default_value
        value: str = internal_value
        return value

    def setValue(self, value: str,
                 value_type: ValueType = ValueType.VALUE) -> None:
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
            internal_value = self._default_value
        SettingsLowLevel.set_setting_str(self.setting_id, internal_value, self.service_id)

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

    def validate(self) -> Tuple[bool, str]:
        valid: bool = True
        internal_value: str = SettingsLowLevel.get_setting_str(self.setting_id, self.service_id)
        if (self.allowed_values is not None) and (len(self.allowed_values) > 0):
            if internal_value not in self.allowed_values:
                valid = False
        if valid and len(internal_value) < self.min_value:
            valid = False
        if valid and len(internal_value) > self.max_value:
            valid = False

        return valid, internal_value

    def preValidate(self, ui_value: str) -> Tuple[bool, str]:
        pass


class EnumValidator(Validator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: int, max_value: int, default_value: int,
                 scale_internal_to_external: int = 1) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.min_value: int = min_value
        self.max_value: int = max_value
        self._default_value: int = default_value
        self.scale_internal_to_external: int = scale_internal_to_external
        return

    def getValue(self, value_type: ValueType = ValueType.VALUE) -> int | float| str:
        pass

    def setValue(self, value: int | float | str,
                 value_type: ValueType = ValueType.VALUE) -> None:
        pass

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> enum.Enum:
        pass

    def getInternalValue(self) -> int | str:
        pass

    def setInternalValue(self, internalValue: int | str) -> None:
        pass

    def validate(self) -> Tuple[bool, Any]:
        pass

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        pass


class ConstraintsValidator(Validator):
    def __init__(self, setting_id: str, service_id: str,
                 constraints: Constraints) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self.constraints: Constraints = constraints

    def setUIValue(self, ui_value: int) -> None:
        pass

    def getUIValue(self) -> int:
        pass

    def getValue(self, value_type: ValueType = ValueType.VALUE) -> int | float | str:
        constraints: Constraints = self.constraints
        value: int | float = constraints.currentValue()
        return value

    def setValue(self, value: int | float | str,
                 value_type: ValueType = ValueType.VALUE) -> None:
        constraints: Constraints = self.constraints
        constraints.setSetting(value, self.service_id)

    def validate(self) -> Tuple[bool, int]:
        constraints: Constraints = self.constraints
        value = SettingsLowLevel.get_setting_int(constraints.property_name, self.service_id)
        in_range: bool = False
        if value is not None:
            value = value * constraints.scale
            in_range = constraints.in_range(value)
        return in_range, value

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        pass

    @property
    def default_value(self):
        return self.constraints.default


class BoolValidator(Validator):
    def __init__(self, setting_id: str, service_id: str,
                 default: bool) -> None:
        super().__init__(setting_id, service_id)
        self.setting_id: str = setting_id
        self.service_id: str = service_id
        self._default: bool = default

    def getValue(self, value_type: ValueType = ValueType.VALUE) -> bool:
        value = SettingsLowLevel.get_setting_bool(self.setting_id, self.service_id,
                                          self._default)
        return value

    def setValue(self, value: bool, value_type: ValueType = ValueType.VALUE) -> None:
        SettingsLowLevel.set_setting_bool(self.setting_id, value, self.service_id)

    def setUIValue(self, ui_value: bool) -> None:
        pass

    def getUIValue(self) -> bool:
        pass

    def getInternalValue(self) -> bool:
        pass

    def setInternalValue(self, internalValue: bool) -> None:
        pass

    def validate(self) -> Tuple[bool, bool]:
        pass

    def preValidate(self, ui_value: bool) -> Tuple[bool, bool]:
        pass
