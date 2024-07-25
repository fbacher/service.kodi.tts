from __future__ import annotations  # For union operator |

import collections
from enum import Enum
from typing import NamedTuple

from common.constants import Constants
from common.logger import BasicLogger

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.i_constraints import IConstraints
from common.setting_constants import Channels, Genders, PlayerMode

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_module_logger(module_path=__file__)
else:
    module_logger = BasicLogger.get_module_logger()


class UIValues(NamedTuple):
    minimum: int | float = 0
    maximum: int | float = 0
    default: int | float = 0
    current: int | float = 0
    increment: int | float = 0
    is_integer: bool = True

    def __repr__(self) -> str:
        return (f'min: {self.minimum} max: {self.maximum} def: {self.default} '
                f'cur: {self.current} inc: {self.increment} int: {self.is_integer}')


class ValueType(Enum):
    VALUE = 0
    INTERNAL = 1
    UI = 2


class INumericValidator:

    def __init__(self, setting_id: str, service_id: str,
                 minimum: int, maximum: int,
                 default: int | None = None,
                 is_decibels: bool = False,
                 is_integer: bool = True,
                 increment: int | float = 0.0) -> None:
        pass

    def get_value(self) -> int | float:
        pass

    def get_raw_value(self) -> int:
        pass

    def set_value(self, value: int | float) -> None:
        pass

    def validate(self, value: int | None) -> bool:
        pass

    def get_minimum(self) -> int:
        pass

    def get_maximum(self) -> int:
        pass

    @classmethod
    def to_percent(cls, value: int | float) -> float:
        pass

    @classmethod
    def to_decibels(cls, value) -> float:
        pass

    @property
    def increment(self):
        pass

    def as_percent(self) -> int | float:
        """
        Converts the value from decibels to percent.

        :return:
        """
        pass

    def as_decibels(self) -> int | float:
        pass

    def get_tts_values(self) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, current_value, minimum_increment,
                 values_are_int: bool)
        """
        pass


class IValidator:

    def __init__(self, setting_id: str, service_id: str,
                 default: Any | None = None, const: bool = False) -> None:
        pass

    def is_const(self) -> bool:
        return None

    def get_const_value(self) -> Any:
        """
        :return: None if this validator is not for a constant value, otherwise,
                 the value is returned. Used immediately after loading from settings.xml
        """
        return None

    def validate(self, value: int | None) -> bool:
        raise NotImplementedError()

    def preValidate(self, value: Any) -> Tuple[bool, Any]:
        raise NotImplementedError()

    @property
    def default_value(self) -> bool | int | float | str:
        raise NotImplementedError()

    def get_tts_values(self) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, current_value, minimum_increment,
                 values_are_int: bool)
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


class AllowedValue:

    def __init__(self, value: str, enabled: bool = True):
        self._value: str = value
        self._enabled: bool = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def value(self) -> str:
        return self._value

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    @classmethod
    def find_value(cls, value: AllowedValue | str,
                   values: List[AllowedValue]) -> AllowedValue | None:
        str_value: str
        if isinstance(value, str):
            str_value = value
        else:
            str_value = value.value

        for av in values:
            av: AllowedValue
            if av.value == str_value:
                return av
        return None

    @classmethod
    def update_enabled_state(cls, engine_values: List[AllowedValue],
                             player_values: List[AllowedValue] |
                                            List[List[AllowedValue]]
                             ) -> List[AllowedValue]:
        """
        The UI displays the AllowedValues for the ENGINE. For any values
        that are not supported on the possible players, mark them as Disabled
        so that they are not selectable.

        :param engine_values: AllowedValues of engine
        :param player_values: The AllowedValues from one or more players
        :return : engine_values with values marked appropriately as enabled
        """
        #
        # Mark all AllowedValues in engine_values that are not available in
        # one or more player_values as disabled. The list elements should all
        # be sorted by label. TODO: Change to use enums
        if isinstance(player_values[0], AllowedValue):
            players_values = [player_values]
        else:
            players_values = player_values

        for engine_value in engine_values:
            engine_value: AllowedValue
            engine_value.set_enabled(True)  # Unmark previous work
            for player in players_values:
                player: List[AllowedValue]
                if not engine_value.enabled:
                    break  # Advance to next engine_value
                for player_value in player:
                    player_value: AllowedValue
                    found: bool = False
                    if player_value == engine_value:
                        # Found, no impact on engine values
                        found = True
                        break
                    if not found:
                        engine_value.set_enabled(False)

        return engine_values

    def _eq_(self, other) -> bool:
        module_logger.debug(f'{self.value} {self.enabled} other: {other}')
        if isinstance(other, str):
            return self._value == other
        if not isinstance(other, type(self)):
            return False
        if not self._enabled:
            return False
        return self._value == other._value

    def __repr__(self) -> str:
        if self._enabled:
            return f'{self._value} enabled'
        return f'{self._value} disabled'

    def __lt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._value < other
        if not isinstance(other, AllowedValue):
            raise TypeError('Must be AllowedValue')
        other: AllowedValue
        return self.value < other.value

    def __le__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._value <= other
        if not isinstance(other, AllowedValue):
            raise TypeError('Must be AllowedValue')
        other: AllowedValue
        return self.value <= other.value

    def __gt__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._value > other
        if not isinstance(other, AllowedValue):
            raise TypeError('Must be AllowedValue')
        other: AllowedValue
        return self.value > other.value

    def __ge__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._value >= other
        if not isinstance(other, AllowedValue):
            raise TypeError('Must be AllowedValue')
        other: AllowedValue

        return self.value >= other.value

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            return item in self._value
        if not isinstance(item, AllowedValue):
            raise TypeError('Must be AllowedValue')
        item: AllowedValue

        # TODO Not sure what to do here
        return item.value in self.value

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self: 'AllowedValue', i: slice | int) -> str:
        return self.value[i]

    def __setitem__(self, i: slice | int, o: str | Iterable[str]) -> None:
        raise NotImplementedError

    def __delitem__(self, i: int | slice) -> None:
        raise NotImplementedError

    def __add__(self, other: Iterable[str]) -> AllowedValue:
        raise NotImplementedError

    def __iadd__(self, other: Iterable[str]) -> AllowedValue:
        raise NotImplementedError

    def __mul__(self, n: int):
        raise NotImplementedError

    def __imul__(self, n: int):
        raise NotImplementedError

    def append(self, item: str) -> None:
        raise NotImplementedError

    def insert(self, i: int, item: str) -> None:
        raise NotImplementedError

    def pop(self, i: int = ...) -> AllowedValue:
        raise NotImplementedError

    def remove(self, item: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def copy(self) -> 'AllowedValue':
        raise NotImplementedError

    def count(self, item: str) -> int:
        raise NotImplementedError

    def index(self, item: str, *args: Any) -> int:
        raise NotImplementedError

    def reverse(self) -> None:
        raise NotImplementedError

    def sort(self, *args: Any, **kwds: Any) -> None:
        raise NotImplementedError

    def extend(self, other: Iterable[str], no_check: bool = False) -> None:
        raise NotImplementedError

    def is_empty(self) -> bool:
        return len(self.value) == 0


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

    def get_allowed_values(self, enabled: bool | None) -> List[AllowedValue] | None:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. For example, while an engine
        may support PlayerMode.SLAVE_FILE an already chosen player may not,
        therefore blocking you from changing the PlayerMode

        :param enabled: If specified, then only return values which have the
                 enabled field == enabled param
        :return: A list of Tuple[<setting>, <enabled | disabled> for every
                 supported value. Those settings which are in conflict with
                 a current setting will be marked disabled (False)
        """
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
                 min_value: Enum, max_value: Enum,
                 default_value: Enum = None) -> None:
        pass

    @property
    def default_value(self) -> Enum:
        raise NotImplementedError()

    def get_tts_value(self) -> Enum:
        raise NotImplementedError()

    def set_tts_value(self, value: Enum) -> None:
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

    def preValidate(self, ui_value: Enum) -> Tuple[bool, Enum]:
        raise NotImplementedError()


class IStrEnumValidator(IValidator):

    # Probably won't work as is, needs generics
    def __init__(self, setting_id: str, service_id: str,
                 min_value: StrEnum, max_value: StrEnum,
                 default_value: StrEnum = None) -> None:
        pass

    @property
    def default_value(self) -> StrEnum:
        raise NotImplementedError()

    def get_tts_value(self) -> StrEnum:
        raise NotImplementedError()

    def set_tts_value(self, value: StrEnum) -> None:
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
        raise NotImplementedError()

    def getValue(self) -> int | float | str:
        raise NotImplementedError()

    def setValue(self, value: int | float | str) -> None:
        raise NotImplementedError()

    def preValidate(self, ui_value: int) -> Tuple[bool, int]:
        raise NotImplementedError()

    def get_constraints(self) -> IConstraints:
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

    def get_value(self) -> str:
        raise NotImplementedError()

    def validate(self, value: Genders | None) -> Tuple[bool, Any]:
        raise NotImplementedError()

    def preValidate(self, ui_value: Enum) -> Tuple[bool, Enum]:
        raise NotImplementedError()


class IChannelValidator(IValidator):

    def __init__(self, setting_id: str, service_id: str,
                 min_value: Channels, max_value: Channels,
                 default_value: Channels = Channels.NO_PREF) -> None:
        super().__init__(setting_id, service_id)
        pass

    @property
    def default_value(self) -> Channels:
        raise NotImplementedError()

    def get_tts_value(self) -> Channels:
        raise NotImplementedError()

    def set_tts_value(self, value: Channels) -> None:
        raise NotImplementedError()

    def setUIValue(self, ui_value: str) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def get_value(self) -> str:
        raise NotImplementedError()

    def getInternalValue(self) -> Channels:
        raise NotImplementedError()

    def setInternalValue(self, internalValue: int | str) -> None:
        raise NotImplementedError()

    def validate(self, value: Channels | None) -> Tuple[bool, Any]:
        raise NotImplementedError()

    def preValidate(self, ui_value: Enum) -> Tuple[bool, Enum]:
        raise NotImplementedError()
