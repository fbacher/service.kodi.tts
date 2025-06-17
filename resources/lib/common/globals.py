# coding=utf-8
from enum import auto, Enum
from typing import ForwardRef

import xbmc

from common.message_ids import MessageUtils

DEBUG_ENABLED: bool = False


class VoiceHintToggle(Enum):
    """
    Provides a multi-press toggle that cycles between:
      Hintting disabled
      Hinting on all of the time
      Hinting only when user pauses for some period of time of no activity (a second?)
    """
    OFF = 0  # Values MUST be consecutive
    ON = auto()
    PAUSE = auto()
    #  LAST_VALUE = PAUSE
    #  FIRST_VALUE = OFF

    def get_msg(self) -> str:
        # Translate to message_id (32050)
        return MessageUtils.get_msg_by_id(self.value + 32050)

    def toggle_value(self) -> ForwardRef('VoiceHintToggle'):
        current_value: ForwardRef('VoiceHintToggle') = Globals.voice_hint
        current_value = VoiceHintToggle((current_value.value + 1) % len(VoiceHintToggle))
        Globals.voice_hint = current_value
        if DEBUG_ENABLED:
            xbmc.log(f'HINT_TOGGLE: {current_value}')
        return current_value


class Globals:
    """
    Simply contains global variables that introduce no extra
    dependencies for users.
    """

    # Used to control the voicing of hint-text for controls
    voice_hint: VoiceHintToggle = VoiceHintToggle.OFF
    voice_silent: bool = False
    using_new_reader: bool = False
