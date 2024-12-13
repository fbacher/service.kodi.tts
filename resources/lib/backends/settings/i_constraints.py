# coding=utf-8
from __future__ import annotations  # For union operator |

from common import *


class IConstraints:

    def __init__(self, minimum: int = 0, default: int = 0, maximum: int = 0,
                 integer: bool = True, decibels: bool = False, scale: float = 1.0,
                 property_name: str = None,
                 midpoint: int | None = None, increment: float = 0.0) -> None:
        raise NotImplementedError()

    @property
    def minimum(self) -> float | int:
        raise NotImplementedError()

    @property
    def default(self) -> float | int:
        raise NotImplementedError()

    @property
    def maximum(self) -> float:
        raise NotImplementedError()

    @property
    def midpoint(self) -> float:
        raise NotImplementedError()

    @property
    def increment(self) -> float:
        raise NotImplementedError()

    def currentValue(self, service_id: str, as_decibels: bool | None = None,
                     limit: bool = True) -> float:
        """
        @service_id: The service (engine, player, etc.) to get this validator's
        property from.
        @as_decibels: Converts between decibel and percentage units.
                     True, convert to decibels
                     False, convert to percentage units (based on the scale
                     configured for this validator)
                     None, use decibels or percentage, as set by constructo
        @limit: Limits the returned value to the range configured for this
                validator
        @return: Returns the current, scaled value of the Setting with this
        constraint's property name. Default values are used, as needed.
        """
        raise NotImplementedError()

    def setSetting(self, value: float, engine_id: str) -> None:
        raise NotImplementedError()

    def is_int(self) -> bool:
        raise NotImplementedError()

    def in_range(self, value: float | int) -> bool:
        raise NotImplementedError()

    def translate(self, other: 'IConstraints', integer: bool = True) -> 'IConstraints':
        raise NotImplementedError()

    def translate_value(self, other: 'IConstraints', value: float,
                        as_decibels: bool | None = None) -> int | float:
        """
        Translates an (external) value of this constraint to an (external) value of
        'other' constraint
        @param other: Specifies the constraint to use for converting the given value
        @param value: (external) value of this constraint to convert
        @param as_decibels: Converts to either decibel or percent scale.
                            True, converts to decibels
                            False, converts to percent scale
                            None does no conversion
        @return: Value scaled appropriately to comply with the other constraint
        """
        raise NotImplementedError()

    def translate_linear_value(self, from_minimum: float,
                               from_maximum: float, from_midpoint: float | None,
                               from_value: float,
                               to_minimum: float, to_maximum: float,
                               to_midpoint: float | None) -> float:
        raise NotImplementedError()

    def db_to_percent(self, value: float) -> float:
        raise NotImplementedError()

    def percent_to_db(self, value: float) -> float:
        raise NotImplementedError()

    @property
    def integer(self) -> bool:
        raise NotImplementedError()
