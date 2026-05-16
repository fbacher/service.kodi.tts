# coding=utf-8
from __future__ import annotations

from pathlib import Path

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum

from backends.settings.service_types import (QualityType, ServiceID)

"""
   Provides a consistent way to represent the important language
   information provided by the various TTS engines. The goal is to
   be able to let the user choose the TTS engine and language from
   among those available on their platform.
"""

from langcodes import Language
from common.setting_constants import Genders


class IEngineVoice:

    """
     The VoiceGroup/voice model was adopted from Piper. A VoiceGroup is a collection
     of one or more voices. A Voice is based on a speaking model that emulates
     the person's voice that it is based on. By tweaking certain parameters,
     the same model can be used to produce a family of significantly different
     sounding voices, but still similar. Piper refers to each member of such
     a family as a 'voice'. When different voices from the same voice,
     the Piper/TTS engine does not have go through the expense of loading
     a different model. Therefore, when the text being voiced has multiple
     voices, it is more efficient to use voices from a common Voice.

    """

    def __init__(self, engine_key: ServiceID,
                 lang: Language,
                 gender: Genders,
                 engine_lang_id: str,
                 e_voice_id: str,
                 engine_vg_id: str | None = None,
                 voice_quality: QualityType = QualityType.UNKNOWN,
                 voice_label: str = None,
                 cache_path_segment: Path | None = None) -> None:

        """
        :param engine_key: Specifies the engine that this voice is for
        :param gender: Specifies the gender, if known
        :param lang: langcodes.Language,
        :param e_voice_id: Identifies a Voice within its VoiceGroup
        :param engine_lang_id: Specifies the engine's id for the language for
                               this voice (engine's don't always use ietf.tag
                               (ex. en-GB)).
        :param voice_quality: QualityType
        :param engine_vg_id: Engine specific code to identify the voice-group
                             that this voice belongs
        :param voice_label: Names the voice, or collection of voices. Does not
                            include Voice Group label
        :param cache_path_segment: Engine-specific portion of cache path that
               is unique for the particular voice being used. Typicaly a concise
               representation of <vg_id>-<voice_id>. Default value is
               vg_id-voice_id
        """
        clz = IEngineVoice

    @property
    def engine_key(self) -> ServiceID:
        raise NotImplemented

    @property
    def lang(self) -> Language:
        raise NotImplemented

    @property
    def gender(self) -> Genders:
        raise NotImplemented

    @property
    def engine_lang_id(self) -> str:
        raise NotImplemented

    @property
    def e_vg_id(self) -> str:
        raise NotImplemented

    @property
    def e_voice_id(self) -> str:
        raise NotImplemented

    @property
    def voice_quality(self) -> QualityType:
        raise NotImplemented

    @property
    def voice_quality_label(self) -> str:
        raise NotImplemented

    @property
    def voice_label(self) -> str:
        """
        Gets the label for this voice

        :return: Only the Voice's label (does not include Voice Group)
        """
        raise NotImplemented

    def full_voice_label(self, with_group: bool = False) -> str:
        """
        Gets user-friendly label for the voice

        :param with_group: If True, then return label including the group info,
                           Otherwise, just give voice information.

        :return: desired label
        """
        raise NotImplemented

    @property
    def cache_path_segment(self) -> Path:
        raise NotImplemented

    @property
    def uid(self) -> str:
        """
        Creates a unique id for this voice. In order to be unique it needs
        to uniquely identify: voice, voice_group, engine. Since
        voices have a quality, then if there is a possibility that two voices
        can have the same id, in which case the uid for the voice should also
        contain the quality. Voice group ids should be able to use their ids
        directly.

        Ex. for Piper Voice_group id = 'floyd' voice id "1" quality='0' the
        unique id could be something like "piper|floyd|1|0"

        This unique id can serve several purposes: 1) to act as a dictionary key
        2) to be used as a voice's value for settings.xml. 3) to be used to tell
        the engine, what voice to use for voice generation.

        Since the engine supplies the methods to create and read the UID engine-specific
        interpreation of the uid can be performed. So if, for example, quality,
        makes no difference in identifying the voice, then it can be ommitted or
        ignored.
        """
        raise NotImplemented

    @classmethod
    def get_instance_for_key(cls, voice_key: str) -> 'IEngineVoice':
        raise NotImplemented

    @property
    def gender_label(self) -> str | None:
        raise NotImplemented

    def __eq__(self, other) -> bool:
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        raise NotImplemented

    def __hash__(self) -> int:
        raise NotImplemented

    def __repr__(self) -> str:
        # if not MY_LOGGER.isEnabledFor(DEBUG_V):
        #     return ''
        raise NotImplemented
