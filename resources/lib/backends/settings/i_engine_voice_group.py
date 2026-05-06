# coding=utf-8
from __future__ import annotations

from backends.settings.lang_utils import LangUtils

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from backends.settings.service_types import QualityType, ServiceID

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
   """

from typing import Any, Dict, Final, ForwardRef, List, Tuple

from langcodes import Language

from common.logger import *
from common.setting_constants import Genders

MY_LOGGER = BasicLogger.get_logger(__name__)


class IEngineVoiceGroup:
    """
    Voice Groups are defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, EngineVoiceGroup
    should only 'inhale' the voice information during settings definition
    and not query other engines during this stage.
    """

    # initialized: bool = False
    # _, _, _, kodi_language = LangUtils.get_kodi_locale_info()
    # kodi_language: Language

    """
     The engine's service_id is used as index for vg_by_engine. Each value 
     is in turn a Dict indexed by locale_id ('en-us'). Finally, the value of the 
     third index is a list of every voice supported by that engine and locale_id.
     
     vg_by_engine: key: ServiceID
                        value: Dict[ietf_tag, List[EngineVoice]]
                        ietf-tag ('en-us')
                        List[EngineVoiceGroup] list of all voice-groups supported by 
                        that engine and locale_id/ietf-tag ('en-us')
    Note that the assumption is that Kodi's language is changed
      very infrequently, usually never. If it is changed, TTS must
      be restarted. Therefore, every EngineVoice in this structure
      will be for the same language (and engine).
    """
    # vg_by_engine: Dict[ServiceID, Dict[str, List[ForwardRef('EngineVoiceGroup')]]] = {}

    # vg_keys: Dict[str, EngineVoiceGroup] = {}
    # Lookup table for EngineVoiceGroup instances
    # Key is provided by get_key()
    # vg_keys: Dict[str, IEngineVoiceGroup] = {}

    def __init__(self, engine_key: ServiceID,
                 lang: Language,
                 gender: Genders,
                 default_voice_id: str,
                 engine_lang_id: str,
                 engine_vg_id: str,
                 voice_quality: QualityType,
                 vg_label: str = None,
                 locale_match: int = -1
                 ):
        """
        Note: Not called directly. Call EngineVoiceManager.add_voice_group instead

        Creates and inserts a voice-group into the proper maps.

        :param engine_key: Same as ServiceID. Specifies which engine
                          this entry applies to
        :param lang: langcode.Language of the voices
        :param gender: Specifies the gender, if known
        :param default_voice_id: Default voice_id
        :param engine_lang_id: Code that engine may use for the language
        :param engine_vg_id: Code that engine may use for the voice-group
        :param voice_quality: 0-5
        :param vg_label: Names the collection that a voice
                                   belongs.
        :param locale_match: Measure of how much THIS lang's locale differs from the
                             current Kodi locale. (Using langcodes.tag_distance).
                             Gives some vague hint it how much the langs may differ
                             in speech.
        """
        raise NotImplemented

    @property
    def uid(self) -> str:
        """
            Unique id for the voice group
        """
        raise NotImplemented

    @property
    def engine_key(self) -> ServiceID:
        raise NotImplemented

    @property
    def gender(self) -> Genders:
        raise NotImplemented

    @property
    def default_voice_id(self) -> str:
        raise NotImplemented

    @property
    def lang(self) -> Language:
        raise NotImplemented

    @property
    def lang_tag(self) -> str:
        """
        Gets the Language.tag for the language-territory
        ex. 'en-US'
        """
        raise NotImplemented

    @property
    def engine_lang_id(self) -> str:
        raise NotImplemented

    @property
    def engine_vg_id(self) -> str:
        raise NotImplemented

    @property
    def voice_quality(self) -> QualityType:
        raise NotImplemented

    @property
    def voice_quality_label(self) -> str:
        raise NotImplemented

    @property
    def vg_name(self) -> str:
        raise NotImplemented

    @property
    def e_voices(self) -> 'Dict[str, EngineVoice]':
        """
        :returns: a ditionary[engine_voice, EngineVoice]
        """
        raise NotImplemented

    @property
    def e_voice(self) -> 'EngineVoice':
        """
        Default voice of the group
        """
        raise NotImplemented

    @property
    def locale_match(self) -> int:
        raise NotImplemented

    def add_voice(self, voice: ForwardRef('IEngineVoice')) -> None:
        raise NotImplemented

    @property
    def has_single_voice(self) -> bool:
        """
        A voice-group can have multiple voices. When there is a single voice,
        the voice-group is treated as just a voice. A SelectionDialog either
        presents a list of EngineVoiceGroups to choose from, or voices.
        """
        raise NotImplemented

    @classmethod
    def get_vg(cls, engine_key: ServiceID | None = None,
               locale: str | None = None,
               vg_id: str | None = None) -> 'EngineVoiceGroup':
        """
        TODO: Consider replacing with either map / a truly unique key
              to do simple lookup.
              Perhaps key = engine_key + langinfo_key + vg_key | voice_key
        Gets the EngineVoiceGroup instance for the given engine and voice_id.

        :param engine_key: Engine to get the voice-group for. If None, then the
                           current engine is used.
        :param locale: Locale to get the voice-group for. If None, then the engine's
                       language setting is used
        :param vg_id: Identifies the voice-group. If None, then the current voice-group
                         for the given engine is used.

        :return: EngineVoiceGroup found, or None
        """
        raise NotImplemented

    @property
    def gender_label(self) -> str:
        raise NotImplemented

    @property
    def vg_label(self) -> str:
        """
        Gets the label for this voice group

        :return: Only the Voice Group's label (
        """
        raise NotImplemented

    @property
    def full_vg_label(self, voice_id: str) -> str:
        """
        Inclues Voice Group's label, if any.

        :param voice_id: Identifies the voice within the group to include in
                         label
        :return: The Voice_Group's label along with the Voice label
        """
        raise NotImplemented

    @property
    def vg_uid(self) -> str:
        raise NotImplemented

    def __repr__(self) -> str:
        raise NotImplemented

    @property
    def voices(self):
        raise NotImplemented

    @property
    def voice_count(self) -> int:
        raise NotImplemented
