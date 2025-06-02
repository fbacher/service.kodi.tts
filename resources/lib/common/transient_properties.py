# coding=utf-8

"""
    Similar to SettingProp, but for only transient settings, which are
    determined at run-time.
"""
from enum import auto

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum


class Transient(StrEnum):
    AUDIO_TYPE_INPUT = 'audio_input'
    AUDIO_TYPE_OUTPUT = 'audio_output'
