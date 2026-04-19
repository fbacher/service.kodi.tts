# coding=utf-8
from __future__ import annotations

from backends.settings.service_types import ServiceID

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
"""

from langcodes import Language


class IEngineLang:
    """
    Voice Information is defined at startup, in bootstrap_engines,
    as part of engine intialization.
    """

    @classmethod
    def init(cls):
        raise NotImplemented

    def __init__(self, engine_key: ServiceID,
                 lang: Language,
                 engine_lang_id: str) -> None:
        """
        :param engine_key: Specifies the engine that this voice is for
        :param lang: langcodes.Language,
        :param engine_lang_id: Specifies the language id of engine (and voice)
        """
        pass

    @property
    def engine_key(self) -> ServiceID:
        raise NotImplemented

    @property
    def lang(self) -> Language:
        raise NotImplemented

    @property
    def label(self) -> str:
        raise NotImplemented

    @property
    def uid(self) -> str:
        raise NotImplemented

    @property
    def engine_lang_id(self) -> str:
        raise NotImplemented

    def set_uid(self) -> str:
        """
        Creates a unique id for this EngineLanguage.

        Id is from concatenation of engine_key and lang.to_tag()
        """
        raise NotImplemented

    @classmethod
    def get_uid(cls, engine_key: ServiceID, ietf_tag: str) -> str:
        raise NotImplemented

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        raise NotImplemented

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        return NotImplemented

    def __repr__(self) -> str:
        raise NotImplemented
