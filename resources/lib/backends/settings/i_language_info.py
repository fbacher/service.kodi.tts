# coding=utf-8
from __future__ import annotations

from backends.settings.i_lang_utils import ILangUtils
from backends.settings.lang_utils import LangUtils

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from backends.settings.service_types import ServiceID

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
   """

from typing import Dict, ForwardRef, List

from langcodes import Language


class ILanguageInfo(LangUtils):
    """
    Language Information is defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, LanguageInfo
    should only 'inhale' the language information during settings definition
    and not query other engines during this stage.
    """

    def __init__(self, engine_key: ServiceID,
                 ietf: Language,
                 engine_lang_id: str):
        """
        :param engine_key: Same as ServiceID. Specifies which engine
                          this entry applies to
        :param ietf: langcodes.Language IETF standard object.
        :param engine_lang_id: Code that engine may use for the language
        :param engine_quality: 0-5 estimated quality rating (0=least)
        """
        super().__init__(engine_key=engine_key,
                         ietf=ietf,
                         engine_lang_id=engine_lang_id)

    @classmethod
    def add_variant(cls,
                    engine_key: ServiceID,
                    ietf: Language,
                    engine_lang_id: str,
                    engine_quality: int
                    ) -> None:
        """
        Creates a language variant ('en-gb') for an engine

        :param engine_key: Specifies which engine this entry applies to
        :param ietf: langcodes.Language IETF standard object. Useful for getting
                     translated messages for any field that it handles. In particular,
                     the language name.
        :param engine_lang_id: Code that engine may use for the language variant
        :param engine_quality: 0-5 estimated quality rating (0=least)
        """
        raise NotImplementedError()

    def get_voice_groups(self) -> 'Dict[str, List[VoiceGroup]]':
        """
        Gets the voice-group information for this instance. There can be multiple
        voices (male, female, Bob, etc.)

        :return: Table indexed by locale containing the voice-groups for this engine and
                locale
        """
        raise NotImplementedError()

    @classmethod
    def load_voice_groups_for_engine(cls, engine_key: ServiceID) -> None:
        """
        Populates the voice_group information for the given engine. There can be
        multiple voice-groups (male, female, Bob, etc.)

        :return: None
        """
        raise NotImplementedError()

    @classmethod
    def get_instance(cls,
                     engine_key: ServiceID | None = None,
                     ietf: Language | None = None) -> ForwardRef('LanguageInfo'):
        """
        Finds the LanguageInfo variant for the given engine and locale_id
        (ietf.to_tag()). Any missing arguments will be filled in with current
        setting values.

        :param engine_key:
        :param ietf: IETF tag ('en-us')
        :return:
        """
        raise NotImplementedError()

    @classmethod
    def get_locale_variants(cls,
                            engine_key: ServiceID | None = None,
                            ietf: Language | None = None
                            ) -> Dict[ServiceID, Dict[str, LanguageInfo]]:
        """
        Gets language capabilities of all or a single TTS engine.

        :param engine_key: If None, then return information for all engines
                       If not None, then return information for the engine
                       identified by this parameter
        :param ietf: Limits returned voice information to the
                     language variant identified by ietf.to_tag
                     (i.e. 'de-de'). If None, then returns all variants
        :return: Dict indexed by service_key. Values are Dicts, indexed and ordered
                 by the locale (ietf.to_tag) with the values being the VoiceGroup
                 objects with the details.
        """
        raise NotImplementedError()

    @classmethod
    def discover_lang_info(cls) -> None:
        """
        Query every engine for supported languages, voices, etc.
        Build data structures required to run engine.
        """
        raise NotImplementedError()

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        raise NotImplementedError()

    def __repr__(self) -> str:
        raise NotImplementedError()
