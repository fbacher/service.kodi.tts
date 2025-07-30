# coding=utf-8
from __future__ import annotations  # For union operator |

import enum
from enum import Enum
from typing import NamedTuple

from backends.settings.service_types import ServiceID
from backends.settings.setting_properties import SettingType
from common.constants import Constants
from common.logger import BasicLogger
from common.service_status import StatusType

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from common import *

from backends.settings.i_constraints import IConstraints
from common.setting_constants import Channels, Genders, PlayerMode

if Constants.INCLUDE_MODULE_PATH_IN_LOGGER:
    module_logger = BasicLogger.get_logger(__name__)
else:
    module_logger = BasicLogger.get_logger(__name__)


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

    @property
    def property_type(self) -> SettingType:
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
        raise NotImplementedError

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

    def __init__(self, service_key: ServiceID,
                 property_type: SettingType,
                 default: Any | None = None,
                 allow_default: bool = True,
                 const: bool = False) -> None:
        self._property_type: SettingType = property_type
        pass

    @property
    def property_type(self) -> SettingType:
        return self._property_type

    def is_const(self) -> bool | None:
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
    def default(self) -> bool | int | float | str:
        raise ValueError('Does not support Default')

    def get_tts_values(self) -> UIValues:
        """
           Gets values suitable for a UI to display and change.

        :return: (min_value, max_value, current_value, minimum_increment,
                 values_are_int: bool)
        """
        raise NotImplementedError()

    def get_tts_value(self, default_value: int | float | str = None) -> int | float | str:
        """

        :param default_value:
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


class ISimpleValidator(IValidator):

    def __init__(self, service_key: ServiceID,
                 property_type: SettingType,
                 const: bool = False) -> None:
        super().__init__(service_key=service_key, property_type=property_type,
                         const=const)
        self._service_key: ServiceID = service_key
        self._property_type: SettingType = property_type
        self._const: bool = const

    @property
    def property_type(self) -> SettingType:
        return self._property_type

    def is_const(self) -> bool | None:
        raise NotImplementedError()

    def get_value(self) -> Any:
        raise NotImplementedError()

    def validate(self, value: int | None) -> bool:
        raise NotImplementedError()

    def preValidate(self, value: Any) -> Tuple[bool, Any]:
        raise NotImplementedError()


class IIntValidator(IValidator):

    def __init__(self, service_key: ServiceID,
                 min_value: int, max_value: int, default_value: int,
                 step: int, scale_internal_to_external: int = 1) -> None:
        raise NotImplementedError()

    @property
    def default(self) -> int | float:
        raise NotImplementedError()

    def get_tts_value(self, default_value: int | float | str = None) -> int | float | str:
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

    def __init__(self, value: str, enabled: bool = True,
                 service_key: ServiceID | None = None):
        self._value: str = value
        self._enabled: bool = enabled
        self._service_key: ServiceID = service_key

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def value(self) -> str:
        return self._value

    @property
    def service_key(self) -> ServiceID:
        return self._service_key

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

    def __eq__(self, other) -> bool:
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

    def __init__(self, service_key: ServiceID,
                 allowed_values: List[str], min_length: int = 0,
                 max_length: int = 4096, default_value: str = None,
                 allow_default: bool = True,
                 const: bool = False
                 ) -> None:
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
        super().__init__(service_key=service_key,
                         property_type=SettingType.STRING_TYPE,
                         default=default_value,
                         allow_default=allow_default,
                         const=const
                         )

    @property
    def property_type(self) -> SettingType:
        return super().property_type

    def get_tts_value(self, default: str | None = None) -> str:
        raise NotImplementedError()

    def set_tts_value(self, value: str) -> None:
        raise NotImplementedError()

    @property
    def default(self) -> str:
        raise NotImplementedError()

    def get_allowed_values(self,
                           enabled: bool | None = None) -> List[AllowedValue] | None:
        """
        Determine which values are allowed and which normally allowed values
        are disabled, due to other settings. For example, while an engine
        may support PlayerMode.SLAVE_FILE an already chosen player_key may not,
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


'''
class IEnumValidator(IValidator):

    # Probably won't work as is, needs generics
    def __init__(self, setting_id: str, property_type: SettingType, service_id: str,
                 min_value: Enum, max_value: Enum,
                 default_value: Enum = None) -> None:
        pass

    @property
    def default(self) -> Enum:
        raise NotImplementedError()

    def get_tts_value(self) -> enum.Enum:
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
'''


class IStrEnumValidator(IValidator):

    def __init__(self, service_key: ServiceID,
                 min_value: StrEnum, max_value: StrEnum,
                 default_value: StrEnum = None) -> None:
        pass

    @property
    def default(self) -> StrEnum:
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

    def __init__(self, service_key: ServiceID, property_type: SettingType,
                 constraints: IConstraints) -> None:
        self.constraints: IConstraints = constraints

    def setUIValue(self, ui_value: int) -> None:
        raise NotImplementedError()

    def getUIValue(self) -> str:
        raise NotImplementedError()

    def get_tts_values(self, default_value: int | float | str = None) \
            -> Tuple[int | float | str, int | float | str, int | float | str, \
                     int | float | str]:
        """
        :param default_value:
        :return: current_value, min_value, default, max_value
        """
        raise NotImplementedError()

    def set_tts_value(self, value: int | float | str) -> None:
        raise NotImplementedError()

    def get_impl_value(self,
                       setting_service_id: str | None = None) -> int | float | str:
        """
            Translates the 'TTS' value (used internally) to the implementation's
            scale (player_key or engine).
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

    def __init__(self, service_key: ServiceID,
                 default: bool, const: bool = False,
                 define_setting: bool = True,
                 service_status: StatusType | None = StatusType.OK,
                 persist: bool = True) -> None:
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

    def __init__(self, service_key: ServiceID,
                 min_value: Genders, max_value: Genders,
                 default_value: Genders = Genders.ANY) -> None:
        super().__init__(service_key, property_type=SettingType.STRING_TYPE)
        pass

    @property
    def default(self) -> Genders:
        raise NotImplementedError()

    @property
    def property_type(self) -> SettingType:
        return SettingType.STRING_TYPE

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

    def preValidate(self, ui_value: Enum) -> Tuple[bool, Enum]:
        raise NotImplementedError()


class IChannelValidator(IValidator):

    def __init__(self, service_key: ServiceID,
                 min_value: Channels, max_value: Channels,
                 default_value: Channels = Channels.NO_PREF) -> None:
        super().__init__(service_key, property_type=SettingType.STRING_TYPE)
        pass

    @property
    def default(self) -> Channels:
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


class IEngineValidator:
    """
    Validator for getting and setting engine ids from Settings.

    Enhancements include verifying if an engine is marked as non-functional.
    If an engine is non-functional, an Exception is thrown indicating that a new
    engine needs to be picked.
    """

    def __init__(self) -> None:
        raise NotImplementedError('')

    def get_service_key(self) -> ServiceID:
        """
        Gets the current engine_id. If the engine is non-functional, then
        a ServiceUnavailable is thrown containing the failing setting_id
        and the reason.
        """
        raise NotImplementedError('')

    def set_service_key(self, engine_key: ServiceID) -> None:
        """
        Sets the current engine_id. If the engine is non-functional, then
        a ServiceUnavailable is thrown containing the failing setting_id
        and the reason.
        """
        raise NotImplementedError('')
