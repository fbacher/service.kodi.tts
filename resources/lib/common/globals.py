# coding=utf-8
from enum import auto, Enum
from typing import ForwardRef

import xbmc

from common.message_ids import MessageId

DEBUG_ENABLED: bool = False


class GlobalValues:
    """
    Simply contains global variables that introduce no extra
    dependencies for users.
    """

    instance = None

    @classmethod
    def class_init(cls) -> None:
        if cls.instance is None:
            cls.instance = GlobalValues()

    def __init__(self) -> None:
        self._voice_hint: MessageId = MessageId.VOICE_HINT_OFF
        self._silent: bool = False
        self._using_new_reader: bool = False

    @property
    def voice_hint(self) -> MessageId:
        return self._voice_hint

    @voice_hint.setter
    def voice_hint(self, value: MessageId) -> None:
        if not isinstance(value, MessageId):
            raise ValueError('Not a MessageId')

        self._voice_hint = value
        if DEBUG_ENABLED:
            xbmc.log(f'HINT_TOGGLE: {self._voice_hint.name}')
        return

    @property
    def toggle_voice_hint(self) -> MessageId:
        """
        Cycles through the possible values
        """
        if self._voice_hint == MessageId.VOICE_HINT_OFF:
            self._voice_hint = MessageId.VOICE_HINT_ON
        elif self._voice_hint == MessageId.VOICE_HINT_ON:
            self._voice_hint = MessageId.VOICE_HINT_PAUSE
        elif self._voice_hint == MessageId.VOICE_HINT_PAUSE:
            self._voice_hint = MessageId.VOICE_HINT_OFF
        if DEBUG_ENABLED:
            xbmc.log(f'HINT_TOGGLE: {self._voice_hint.name}')
        return self._voice_hint

    @property
    def using_new_reader(self) -> bool:
        return self._using_new_reader

    @using_new_reader.setter
    def using_new_reader(self, using_new: bool) -> None:
        self._using_new_reader = using_new

    @property
    def silent(self) -> bool:
        return self._silent

    @silent.setter
    def silent(self, silent: bool) -> None:
        self._silent = silent


class Globals:
    """
    Simply contains global variables that introduce no extra
    dependencies for users.
    """

    GlobalValues.class_init()

    @staticmethod
    def get_voice_hint() -> MessageId:
        return GlobalValues.instance.voice_hint

    @staticmethod
    def set_voice_hint(value: MessageId) -> None:
        inst: GlobalValues = GlobalValues.instance
        inst.voice_hint = value

    @staticmethod
    def toggle_voice_hint() -> MessageId:
        """
        Cycles through the possible values
        """
        inst: GlobalValues = GlobalValues.instance
        return inst.toggle_voice_hint

    @staticmethod
    def is_using_new_reader() -> bool:
        inst: GlobalValues = GlobalValues.instance
        return inst.using_new_reader

    @staticmethod
    def set_using_new_reader(using_new: bool) -> None:
        inst: GlobalValues = GlobalValues.instance
        inst.using_new_reader = using_new

    @staticmethod
    def is_silent() -> bool:
        inst: GlobalValues = GlobalValues.instance
        return inst.silent

    @staticmethod
    def set_silent(silent: bool) -> None:
        inst: GlobalValues = GlobalValues.instance
        inst.silent = silent
