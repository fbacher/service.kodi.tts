# coding=utf-8

from common.typing import *


class Constraints:
    def __init__(self, minimum: int = 0, default: int = 0,
                 maximum: int = 0, integer: bool = True):
        super().__init__()
        self.minimum: int = minimum
        self.default: int = default
        self.maximum: int = maximum
        self.integer: bool = integer

    def translate(self, other: 'Constraints', integer: bool = True) -> 'Constraints':
        # Normalize both constraints

        scale = float((other.maximum - other.minimum)) / float(
                (self.maximum - self.minimum))

        trans_constraints: Constraints = \
            Constraints(int((float(self.minimum - self.minimum) * scale) + other.minimum),
                        int((float(self.default - self.minimum) * scale) + other.minimum),
                        int((float(self.maximum - self.minimum) * scale) + other.minimum),
                        integer)
        return trans_constraints

    def translate_value(self, other: 'Constraints', value: float,
                        integer: bool = False) -> int | float:
        scale: float = (float(other.maximum) - float(other.minimum)) / (
                float(self.maximum) - float(self.minimum))

        trans_value: float = (((value - float(self.minimum)) * scale) + other.minimum)
        if integer:
            return int(trans_value)
        return trans_value
