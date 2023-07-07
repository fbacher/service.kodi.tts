import enum

from strenum import StrEnum

from backends.settings.i_constraints import IConstraints
from common.setting_constants import Genders
from common.typing import *


class ValueType(enum.Enum):
    VALUE = 0
    INTERNAL = 1
    UI = 2


class IValidator:

    def __init__(self, setting_id: str, engine_id: str) -> None:
        pass

    def validate(self, value: int | None) -> bool:
        raise Exception('Not Implemented')

    def preValidate(self, value: Any) -> Tuple[bool, Any]:
        raise Exception('Not Implemented')

    @property
    def default_value(self) -> bool | int | float | str:
        raise Exception('Not Implemented')

    def getValue(self) -> bool | int | float| str:
        raise Exception('Not Implemented')

    def setValue(self, value: bool | int | float | str) -> None:
        raise Exception('Not Implemented')

    # Causes Trouble
    # @property
    # def default(self):
    #     raise NotImplementedError()


class IIntValidator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: int, max_value: int, default_value: int,
                 step: int, scale_internal_to_external: int = 1) -> None:
       pass

    @property
    def default_value(self) -> int | float:
        raise Exception('Not Implemented')

    def getValue(self, default_value: int | None = None) -> int | float:
        raise NotImplementedError()

    def setValue(self, value: int | float) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value:int) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> int:
        raise NotImplementedError()

    def getInternalValue(self) -> int:
        raise NotImplementedError()

    def setInternalValue(self, value: int) -> None:
        raise NotImplementedError()

    def getLabel(self) -> str:
        raise NotImplementedError()

    def getUnits(self) -> str:
        raise NotImplementedError()

    def validate(self, value: int | None) -> bool:
        raise NotImplementedError()

    def preValidate(self, ui_value: int) -> bool:
        raise NotImplementedError()

    def get_min_value(self) -> int:
        raise NotImplementedError()

    def get_max_value(self) -> int:
        raise NotImplementedError()

    def get_default_value(self) -> int:
        raise NotImplementedError()


class IStringValidator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default_value: str = None) -> None:
        pass

    @property
    def default_value(self) -> str:
        raise Exception('Not Implemented')

    def getValue(self, default_value : str | None = None) -> str:
        raise NotImplementedError()

    def setValue(self, value: str) -> None:
        raise NotImplementedError()

    def get_allowed_values(self) -> List[str] | None:
        raise NotImplementedError()

    def setUIValue(self, ui_value:str) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> str:
        raise NotImplementedError()

    def setInternalValue(self, value: str) -> None:
        raise NotImplementedError()

    def getLabel(self) -> str:
        raise NotImplementedError()

    def getUnits(self) -> str:
        raise NotImplementedError()

    def validate(self, value: str | None) -> Tuple[bool, str]:
        raise NotImplementedError()

    def preValidate(self, ui_value: str) -> Tuple[bool, str]:
        raise NotImplementedError()


class IEnumValidator(IValidator):
    # Probably won't work as is, needs generics
    def __init__(self, setting_id: str, service_id: str,
                 min_value: enum.Enum, max_value: enum.Enum,
                 default_value: enum.Enum = None) -> None:
        pass

    @property
    def default_value(self) -> enum.Enum:
        raise Exception('Not Implemented')

    def getValue(self) -> enum.Enum:
        raise NotImplementedError()

    def setValue(self, value: enum.Enum) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: int) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> int:
        raise NotImplementedError()

    def getInternalValue(self) -> int | str:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError()

    def validate(self) -> Tuple[bool, Any]:
        raise NotImplementedError()

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError()


class IStrEnumValidator(IValidator):
    # Probably won't work as is, needs generics
    def __init__(self, setting_id: str, service_id: str,
                 min_value: StrEnum, max_value: StrEnum,
                 default_value: StrEnum = None) -> None:
        pass

    @property
    def default_value(self) -> StrEnum:
        raise Exception('Not Implemented')

    def getValue(self) -> StrEnum:
        raise NotImplementedError()

    def setValue(self, value: StrEnum) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: str) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> StrEnum:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: StrEnum) -> None:
        raise NotImplementedError()

    def validate(self) -> Tuple[bool, StrEnum]:
        raise NotImplementedError()

    def preValidate(self, ui_value: StrEnum) -> Tuple[bool, StrEnum]:
        raise NotImplementedError()


class IConstraintsValidator:
    def __init__(self, setting_id: str, service_id: str,
                 constraints: IConstraints) -> None:
        pass

    @property
    def default_value(self) -> int | float | str:
        raise Exception('Not Implemented')

    def setUIValue(self, ui_value: int) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getValue(self) -> int | float | str:
        raise NotImplementedError()

    def setValue(self, value: int | float | str) -> None:
        raise NotImplementedError()

    def validate(self) -> Tuple[bool, int]:
        raise NotImplementedError()

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        raise NotImplementedError()

    def get_min_value(self) -> int:
        raise NotImplementedError()

    def get_max_value(self) -> int:
        raise NotImplementedError()

    def get_default_value(self) -> int:
        raise NotImplementedError()

    def get_constraints(self) -> IConstraints:
        return self.constraints


class IBoolValidator:
    def __init__(self, setting_id: str, service_id: str,
                 default: bool) -> None:
        pass

    @property
    def default_value(self) -> bool:
        raise Exception('Not Implemented')

    def getValue(self) -> bool:
        raise NotImplementedError()

    def setValue(self, value: bool) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: bool) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> bool:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: bool) -> None:
        raise NotImplementedError()

    def validate(self) -> Tuple[bool, bool]:
        raise NotImplementedError()

    def preValidate(self, ui_value: bool) -> Tuple[bool, bool]:
        raise NotImplementedError()


class IGenderValidator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: Genders, max_value: Genders,
                 default_value: Genders = Genders.UNKNOWN) -> None:
        super().__init__(setting_id, service_id)
        pass

    @property
    def default_value(self) -> Genders:
        raise Exception('Not Implemented')

    def getValue(self) -> Genders:
        raise NotImplementedError()

    def setValue(self, value: Genders) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: str) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> Genders:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError()

    def validate(self, value: Genders | None) -> Tuple[bool, Any]:
        raise NotImplementedError()

    def preValidate(self, ui_value: enum.Enum) -> Tuple[bool, enum.Enum]:
        raise NotImplementedError()
