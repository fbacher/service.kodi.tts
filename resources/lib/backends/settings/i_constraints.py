# coding=utf-8

from common.typing import *


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

    def currentValue(self, service_id: str) -> float:
        raise NotImplementedError()

    def setSetting(self, value: float, backend_id: str) -> None:
        raise NotImplementedError()

    def is_int(self) -> bool:
        raise NotImplementedError()

    def in_range(self, value: float | int) -> bool:
        raise NotImplementedError()

    def translate(self, other: 'IConstraints', integer: bool = True) -> 'IConstraints':
        raise NotImplementedError()

    def translate_value(self, other: 'IConstraints', value: float) -> int | float:
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
