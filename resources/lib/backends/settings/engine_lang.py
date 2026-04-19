# coding=utf-8
from __future__ import annotations


try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from backends.settings.service_types import ServiceID, ServiceKey, SERVICES_BY_TYPE

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
"""

from typing import Any, Dict, Final, ForwardRef, List, Tuple

from langcodes import Language

from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class EngineLang:
    """
    Voice Information is defined at startup, in bootstrap_engines,
    as part of engine intialization.
    """

    initialized: bool = False

    @classmethod
    def init(cls):
        pass

    def __init__(self, engine_key: ServiceID,
                 lang: Language,
                 engine_lang_id: str) -> None:
        """
        :param engine_key: Specifies the engine that this voice is for
        :param lang: langcodes.Language,
        :param engine_lang_id: Specifies the language id of engine (and voice)
        """

        clz = EngineLang
        self._engine_key: ServiceID = engine_key
        self._lang: Language = lang
        self._engine_lang_id: str = engine_lang_id
        self._label: str | None = None
        self._uid: str = ''
        self.set_uid()
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'{self}')

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def lang(self) -> Language:
        return self._lang

    @property
    def label(self) -> str:
        return self._label

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def engine_lang_id(self) -> str:
        return self._engine_lang_id

    def set_uid(self) -> str:
        """
        Creates a unique id for this EngineLanguage.

        Id is from concatenation of engine_key and lang.to_tag()
        """
        clz = type(self)
        uid: str = clz.get_uid(self._engine_key, self._lang.to_tag())
        self._uid = uid
        return uid

    @classmethod
    def get_uid(cls, engine_key: ServiceID, ietf_tag: str) -> str:
        uid: str = ServiceID.get_uid(engine_key, ietf_tag)
        return f'{uid}'

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        result: str = f'Formatted_lang: {lang}'
        return result

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        if isinstance(other, EngineLang):
            other: EngineLang
            return self._engine_key == other._engine_key
        return NotImplemented

    def __repr__(self) -> str:
        if not MY_LOGGER.isEnabledFor(DEBUG_V):
            return ''

        return f'eng: {self._engine_key} lang: {self._lang}'
