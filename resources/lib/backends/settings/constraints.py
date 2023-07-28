# coding=utf-8
import math

from common.settings_bridge import SettingsBridge
from common.typing import *


class Constraints:
    """
        Define constraints on a propertie's value, including information about how
        to transform from one constraint to another, for example from espeak volume
        to mplayer volume.

        To simplify reading and modifying settings manually, it is advantageous to
        define values so that they are integers. Scale is provided to convert the
        integral values of mininum, maximum, etc. into the float (or even int) values
        that the api requires. For example, mplayer represent speed as:
        0.25 = 1/4 x , 1.0 = 1x, 2.0 = 2x, etc.. Therefore, it's Constraint is defined
        as minimum = 25, maximum = 400 (mplayer supports a wider range, but it seems
        that 1/4x .. 4x is a reasonable practical range, and more likely to be
        supported by other engines/players).

        As a result of the scaling, self._minimum contains the unscaled, integral
        value, (ex '25) while the @property minimum contains self._minimum * self._scale,
        which (ex. 0.25) which is the value used by the (mplayer) api.

        integer determines whether the returned values are integer or float.

        decibels determines whether the values represent decible (logarthmic) or linear.
        This is needed for converting from decibel to linear valumes

        scale, as mentioned earlier, is used to scale an internal, usually integral value,
        to an external, typically float, api, value.

        property_name is the same as property key used in Settings (ex. SettingsProperties.VOLUME)

        midpoint is the value of the logical 'zero reference point' in the range. For example,
        using decibels, zero represents a gain of 1x. similarly, using percent to
        represent volume, 0 can also represent a gain of 1x while -25 represents a 25%
        decrease in volume, while +100 represents a doubling of volume. Like the
        decibel property, midpoint is useful for conversions since it allows you to
        calibrate to a common reference.

         increment is the suggested step between values displayed in the UI.

        """
    def __init__(self, minimum: int = 0, default: int = 0, maximum: int = 0,
                 integer: bool = True, decibels: bool = False, scale: float = 1.0,
                 property_name: str = None,
                 midpoint: int | None = None, increment: float = 0.0,
                 tts_line_value: float | int = 0) -> None:
        """
        @note: Read the class comments for more information
        @param minimum: Minimum internal value that this constrant can have
        @param default: Default internal value for a value using this constraint
        @param maximum: Maximum internal value that this constraint can have
        @param integer: Indicates that values returned by this class are integer
        or float.
        @param decibels: Indicates that the range of values represented by this
        constraint uses a logarithmic (base 10) scale, rather than linear. Used
        for conversions.
        @param scale: Used to scale internal, typically integral, values to api
                      values
        @param property_name: Defines the property that this constraint applies to
        @param midpoint: is the value of the logical 'zero reference point' in the range.
                         Defines common reference point for conversions. Default value
                         is (maximum - minimum) / 2
        @param increment:  is the suggested step between values displayed in the UI.
        """
        super().__init__()
        self._minimum: Final[int] = minimum  # Internal minimum value

        self._default: Final[int] = default
        self._maximum: Final[int] = maximum  # Internal maximum value
        self.integer: Final[bool] = integer
        self._decibels: Final[bool] = decibels
        # Scale factor to convert internal to external value
        self.scale: Final[float] = scale
        self.property_name: Final[str] = property_name
        self._increment: Final[float] = increment
        # if midpoint is None:
        #    midpoint = (maximum + minimum) / 2
        self._midpoint: Final[int | None]  = midpoint
        self._tts_line_value: float | int = tts_line_value

    @property
    def minimum(self) -> float | int:
        """
        @return: External, minimum value of this constraint
        """
        value: float = self._minimum * self.scale
        if self.integer:
            return int(round(value))
        return value

    @property
    def default(self) -> float | int:
        """
        @return: External, default value of this constraint
        """
        value: float = self._default * self.scale
        if self.integer:
            return int(round(value))
        return value

    @property
    def maximum(self) -> float | int:
        """
        @return: External, maximum value of this constraint
        """
        value: float = self._maximum * self.scale
        if self.integer:
            return int(round(value))
        return value

    @property
    def midpoint(self) -> float | int:
        """
        @return:
        """
        if self._midpoint is None:
            return None

        value = self._midpoint * self.scale
        if self.integer:
            return int(round(value))
        return value

    @property
    def increment(self) -> float:
        """
        @return: Suggested increment between possible values in UI. Most useful
        for a slider, or similar
        """
        if self.integer:
            return int(round(self._increment))
        return self._increment

    @property
    def tts_line_value(self) -> float | int:
        return self._tts_line_value

    def currentValue(self, service_id: str) -> float:
        """
        @return: Returns the current, scaled value of the Setting with this
        constraint's property name. Default values are used, as needed.
        """
        if self.property_name:
            raw_value: float = float(
                    SettingsBridge.getSetting(self.property_name,
                                              backend_id=service_id,
                                              default_value=self._default))
            value = raw_value * self.scale
            # if value is out of bounds, change to be either the
            # minimum or maximum value of field, whichever is closest

            corrected: bool
            corrected_value: float
            corrected, corrected_value = self.in_range(value)
            if self.integer:
                return int(round(corrected_value))
            return corrected_value
        return None

    def setSetting(self, value: float, backend_id: str) -> None:
        """
        @param value: External representation of value to be saved (after scaling)
        to the settings cache.
        @param backend_id: The id of the speech engine that this setting applies.
        May be None or empty string if this is a global setting.
        @return: None
        @note: See Settings for information about how settings cache, etc. works
        """
        value: int = int(float(value) / self.scale)
        if self.property_name:
            SettingsBridge.setSetting(self.property_name, value, backend_id)
        return None

    def is_int(self) -> bool:
        return self.integer

    def in_range(self, value: float | int) -> Tuple[bool, float | int]:
        """
        @param value: (External) Value to verify if is within range
        @return: True if given value is within minimum and maximum values
        """
        corrected_value: float = value
        corrected_value = max(value, self.minimum)
        corrected_value = min(corrected_value, self.maximum)
        changed: bool = corrected_value == value
        return changed, corrected_value

    def translate(self, other: 'Constraints', integer: bool = True) -> 'Constraints':
        """
        Experimental
        @param other:
        @param integer:
        @return:
        """
        # Normalize both constraints

        scale = float((other.maximum - other.minimum)) / float(
                (self.maximum - self.minimum))

        trans_constraints: Constraints = Constraints(
                int((float(self.minimum - self.minimum) * scale) + other.minimum),
                int((float(self.default - self.minimum) * scale) + other.minimum),
                int((float(self.maximum - self.minimum) * scale) + other.minimum),
                integer)
        return trans_constraints

    def translate_value(self, other: 'Constraints', value: float) -> int | float:
        """
        Translates an (external) value of this constraint to an (external) value of
        'other' constraint
        @param other: Specifies the constraint to use for converting the given value
        @param value: (external) value of this constraint to convert
        @return: Value scaled appropriately to comply with the other constraint
        """
        value = max(value, self.minimum)
        value = min(value, self.maximum)
        scaled_value:float
        if self._decibels and other._decibels:
            value = max(value, other.minimum)
            value = min(value, other.maximum)
            if other.integer:
                return int(round(value))
            return value

        elif self._decibels:
            scaled_value: float = self.db_to_percent(int(value))
            min_percent: float = self.db_to_percent(self.minimum)
            max_percent: float = self.db_to_percent(self.maximum)
            midpoint_percent: float = self.db_to_percent(self.midpoint)
            scaled_value = self.translate_linear_value(min_percent, max_percent,
                                                       midpoint_percent, scaled_value,
                                                       other.minimum, other.maximum,
                                                       other.midpoint)

            if other.integer:
                scaled_value = round(scaled_value)
            scaled_value = max(scaled_value, other.minimum)
            scaled_value = min(scaled_value, other.maximum)
            if other.integer:
                scaled_value = int(round(scaled_value))
            return scaled_value

        elif other._decibels:
            scaled_value: float = self.percent_to_db(value)
            scaled_value = max(scaled_value, other.minimum)
            scaled_value = min(scaled_value, other.maximum)
            #midpoint: float = 0.0
            #scaled_value = self.translate_linear_value(min_percent, max_percent,
            #                                           midpoint, scaled_value,
            #                                           other.minimum, other.maximum,
            #                                           other.midpoint)
            if other.integer:
                scaled_value = round(scaled_value)
            scaled_value = max(scaled_value, other.minimum)
            scaled_value = min(scaled_value, other.maximum)
            if other.integer:
                scaled_value = int(round(scaled_value))
            return scaled_value

        scaled_value = self.translate_linear_value(self.minimum, self.maximum,
                                           self.midpoint, value, other.minimum,
                                           other.maximum, other.midpoint)
        if other.integer:
            scaled_value = round(scaled_value)
        scaled_value = max(scaled_value, other.minimum)
        scaled_value = min(scaled_value, other.maximum)
        if other.integer:
            scaled_value = int(round(scaled_value))
        return scaled_value

    def translate_linear_value(self, from_minimum: float,
                               from_maximum: float, from_midpoint: float | None,
                               from_value: float,
                               to_minimum: float, to_maximum: float,
                               to_midpoint: float | None) -> float:
        # OldRange = (OldMax - OldMin)
        # NewRange = (NewMax - NewMin)
        # NewValue = (((OldValue - OldMin) * NewRange) / OldRange) + NewMin
        from_range: float
        to_range: float
        to_offset: float
        from_offset: float
        if from_midpoint is None:
            from_range = from_maximum - from_minimum
            from_offset = from_minimum
            to_range = to_maximum - to_minimum
            to_offset = to_minimum
        elif from_value >= from_midpoint:
            from_range = from_maximum - from_midpoint
            from_offset = from_midpoint
            if to_midpoint is None:
                to_range = to_maximum - to_minimum
                to_offset = to_minimum
            else:
                to_range = to_maximum - to_midpoint
                to_offset = to_midpoint
        else:
            from_range = from_midpoint - from_minimum
            from_offset = from_minimum
            if to_midpoint is None:
                to_range = to_maximum - to_minimum
                to_offset = to_minimum
            else:
                to_range = to_midpoint - to_minimum
                to_offset = to_minimum

        trans_value: float
        trans_value = (((from_value - from_offset) * to_range) / from_range) + to_offset
        # scale: float = (to_maximum - to_minimum) / (from_maximum - from_minimum)
        # trans_value = (from_value * scale) + to_minimum
        return trans_value

        '''
        lower_scale: float = (to_midpoint - to_minimum) / (from_midpoint - from_minimum)

        upper_scale: float = (to_maximum - to_midpoint) / (from_maximum - from_midpoint)

        trans_value: float
        if from_value <= from_midpoint:
            trans_value = (from_value * lower_scale) + to_minimum
        else:
            trans_value = (from_value * upper_scale) + to_midpoint

        return trans_value
        '''

    def db_to_percent(self, value: float) -> float:
        value = max(value, self.minimum)
        value = min(value, self.maximum)
        result = int(round(100 * (10 ** (value / 20.0))))
        return result

    def percent_to_db(self, value: float) -> float:
        value = max(value, self.minimum)
        value = min(value, self.maximum)
        result: float = 10.0 * math.log10(float(value) / 100.0)
        return result
