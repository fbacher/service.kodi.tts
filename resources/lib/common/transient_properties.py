# coding=utf-8

"""
    Similar to SettingsProperties, but for only transient settings, which are
    determined at run-time.
"""
from enum import auto

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum


class Transient(StrEnum):
    AUDIO_TYPE_INPUT = auto()
    AUDIO_TYPE_OUTPUT = auto()
