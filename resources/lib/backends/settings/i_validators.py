import enum

from common.typing import *


class ValueType(enum.Enum):
    VALUE = 0
    INTERNAL = 1
    UI = 2


class IValidator:

    def __init__(self, setting_id: str, engine_id: str) -> None:
        self._default_value = None

    def validate(self) -> Tuple[bool, Any]:
        raise Exception('Not Implemented')

    def preValidate(self, value: Any) -> Tuple[bool, Any]:
        raise Exception('Not Implemented')

    def getValue(self, value_type: ValueType = ValueType.VALUE) -> bool | int | float| str:
        raise Exception('Not Implemented')

    def setValue(self, value: bool | int | float | str,
                 value_type: ValueType = ValueType.VALUE) -> None:
        raise Exception('Not Implemented')

    @property
    def default_value(self):
        return self._default_value
