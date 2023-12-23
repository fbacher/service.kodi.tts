import enum

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
        raise NotImplementedError()

    def preValidate(self, value: Any) -> Tuple[bool, Any]:
        raise NotImplementedError()

    @property
    def default_value(self) -> bool | int | float | str:
        raise NotImplementedError()

    def get_tts_values(self, default_value: int | float | str = None,
                       setting_service_id: str = None) \
            -> Tuple[int | float | str, int | float | str, int | float | str, \
                     int | float | str]:
        """

        :param default_value:
        :param setting_service_id:
        :return: current_value, min_value, default_value, max_value
        """
        raise NotImplementedError()

    def get_tts_value(self, default_value: int | float | str = None,
                      setting_service_id: str = None) -> int | float | str:
        """

        :param default_value:
        :param setting_service_id:
        :return: current_value
        """
        raise NotImplementedError()

    def set_tts_value(self, value: bool | int | float | str) -> None:
        raise NotImplementedError()

    def get_constraints(self) -> 'IConstraints':
        raise NotImplementedError()

    @property
    def tts_line_value(self) -> int | float:
        raise NotImplementedError()

    @property
    def integer(self) -> bool:
        raise NotImplementedError()

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
        raise NotImplementedError()

    def get_tts_value(self, default_value: int | None = None) -> int | float:
        raise NotImplementedError()

    def set_tts_value(self, value: int | float) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: int) -> None:
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


class IStringValidator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default_value: str = None) -> None:
        pass

    def get_tts_value(self, default: str | None = None,
                      setting_service_id: str = None) -> str:
        raise NotImplementedError()

    def set_tts_value(self, value: str) -> None:
        raise NotImplementedError()

    @property
    def default_value(self) -> str:
        raise NotImplementedError()

    def get_allowed_values(self) -> List[str] | None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: str) -> None:
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
        raise NotImplementedError()

    def get_tts_value(self) -> enum.Enum:
        raise NotImplementedError()

    def set_tts_value(self, value: enum.Enum) -> None:
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
                 min_value: enum.StrEnum, max_value: enum.StrEnum,
                 default_value: enum.StrEnum = None) -> None:
        pass

    @property
    def default_value(self) -> enum.StrEnum:
        raise NotImplementedError()

    def get_tts_value(self) -> enum.StrEnum:
        raise NotImplementedError()

    def set_tts_value(self, value: enum.StrEnum) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: str) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> enum.StrEnum:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: enum.StrEnum) -> None:
        raise NotImplementedError()

    def validate(self) -> Tuple[bool, enum.StrEnum]:
        raise NotImplementedError()

    def preValidate(self, ui_value: enum.StrEnum) -> Tuple[bool, enum.StrEnum]:
        raise NotImplementedError()


class IConstraintsValidator:

    def __init__(self, setting_id: str, service_id: str,
                 constraints: IConstraints) -> None:
        pass

    def setUIValue(self, ui_value: int) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def get_tts_values(self, default_value: int | float | str = None,
                       setting_service_id: str = None) \
            -> Tuple[int | float | str, int | float | str, int | float | str, \
                     int | float | str]:
        """
        :param default_value:
        :param setting_service_id:
        :return: current_value, min_value, default_value, max_value
        """
        raise NotImplementedError()

    def set_tts_value(self, value: int | float | str) -> None:
        raise NotImplementedError()

    def get_impl_value(self,
                       setting_service_id: str | None = None) -> int | float | str:
        """
            Translates the 'TTS' value (used internally) to the implementation's
            scale (player or engine).
            :return:
        """
        raise NotImplementedError()

    def set_impl_value(self, value: int | float | str) -> None:
        raise NotImplementedError()

    @property
    def tts_line_value(self) -> int | float:
        raise NotImplementedError()

    @property
    def integer(self) -> bool:
        raise NotImplementedError()

    def validate(self, value: int | float | None) -> Tuple[bool, int | float]:
        constraints: IConstraints = self.constraints
        raise NotImplementedError()

    def getValue(self) -> int | float | str:
        raise NotImplementedError()

    def setValue(self, value: int | float | str) -> None:
        raise NotImplementedError()

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        raise NotImplementedError()

    def get_constraints(self) -> IConstraints | IConstraints:
        raise NotImplementedError()

    @property
    def default_value(self) -> int | str | float:
        raise NotImplementedError()

    def get_min_value(self) -> int | float:
        raise NotImplementedError()

    def get_max_value(self) -> int | float:
        raise NotImplementedError()

    '''
    def get_default_value(self) -> int | float | str:
        raise NotImplementedError()
    '''


class IBoolValidator:

    def __init__(self, setting_id: str, service_id: str,
                 default: bool) -> None:
        pass

    @property
    def default_value(self) -> bool:
        raise NotImplementedError()

    def get_tts_value(self) -> bool:
        raise NotImplementedError()

    def set_tts_value(self, value: bool) -> None:
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
        raise NotImplementedError()

    def get_tts_value(self) -> Genders:
        raise NotImplementedError()

    def set_tts_value(self, value: Genders) -> None:
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
