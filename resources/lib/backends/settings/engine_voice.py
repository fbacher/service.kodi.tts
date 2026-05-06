# coding=utf-8
from __future__ import annotations

from pathlib import Path

from backends.settings.i_engine_voice import IEngineVoice
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from backends.settings.i_engine_voice_manager import IEngineVoiceManager

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

from typing import Dict

from langcodes import Language

from common.logger import *
from common.setting_constants import Genders

MY_LOGGER = BasicLogger.get_logger(__name__)


class EngineVoice(IEngineVoice):
    """
    Voice Information is defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, EngineVoice
    should only 'inhale' the voice information during settings definition
    and not query other engines during this stage.
    """

    initialized: bool = False
    all_voices_loaded: bool = False
    _number_of_voices: int = 0
    # Map to all voices. First index is engine_id, second is voice.get_uid()
    _voice_by_engine: Dict[str, Dict[str, 'EngineVoice']] = {}

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
                 real_voice_id: str,
                 engine_vg_id: str | None = None,
                 voice_quality: QualityType = QualityType.UNKNOWN,
                 voice_label: str = None,
                 cache_path_segment: Path | None = None) -> None:

        """
        :param engine_key: Specifies the engine that this voice is for
        :param gender: Specifies the gender, if known
        :param lang: langcodes.Language,
        :param e_voice_id: Identifies a Voice within its VoiceGroup
        :param real_voice_id: Identifies a voice to the Engine for voicing. Default
                              is e_voice_id.
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
        clz = EngineVoice
        clz._number_of_voices += 1
        self._engine_key: ServiceID = engine_key
        self._lang: Language = lang
        self._gender: Genders = gender
        self._engine_lang_id: str = engine_lang_id
        self._e_voice_id: str = e_voice_id
        self._real_voice_id: str = real_voice_id
        self._engine_vg_id: str | None = engine_vg_id
        self._voice_quality: QualityType = voice_quality
        self._gender_label: str | None = None
        self._voice_label: str = voice_label
        self._voice_uid: str | None = None
        if cache_path_segment is None:
            cache_path_segment = f'{engine_vg_id}-{e_voice_id}'
        self._cache_path_segment: Path = Path(cache_path_segment)
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'cache_path_segment: {self._cache_path_segment} '
                               f'engine_key: {engine_key} '
                               f'engine_vg_id: {engine_vg_id} e_voice_id: '
                               f'{e_voice_id} voice_label: {self.voice_label}')

        # if MY_LOGGER.isEnabledFor(DEBUG):
        #     MY_LOGGER.debug(f'{self}')

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def lang(self) -> Language:
        return self._lang

    @property
    def gender(self) -> Genders:
        return self._gender

    @property
    def engine_lang_id(self) -> str:
        return self._engine_lang_id

    @property
    def engine_vg_id(self) -> str:
        return self._engine_vg_id

    @property
    def e_voice_id(self) -> str:
        """
        A unique id within a voice group for this voice.

        Used together with e_vg_id as part of the UID in settings. Also used for
        table lookup.
        """
        return self._e_voice_id

    @property
    def real_voice_id(self) -> str:
        """
        The voice id that the engine is expecting to generate a voice. Used in
        tandem with the e_vg_id, as needed by the engine.

        Default value is e_voice_id
        """
        return self._real_voice_id

    @property
    def voice_quality(self) -> QualityType:
        return self._voice_quality

    @property
    def voice_quality_label(self) -> str:
        return self._voice_quality.label

    @property
    def voice_label(self) -> str:
        """
        Gets the label for this voice

        :return: Only the Voice's label (does not include Voice Group)
        """
        return self._voice_label

    def full_voice_label(self, e_vg: IEngineVoiceGroup | None = None,
                         with_group: bool = False) -> str:
        """
        Gets user-friendly label for the voice

        :param e_vg: EngineVoiceGroup reference for given voice. If None, will
                     look it up
        :param with_group: If True, then return label including the group info,
                           Otherwise, just give voice information.

        :return: desired label
        """
        if e_vg is None:
            e_vg: IEngineVoiceGroup = IEngineVoiceManager.get_vg(self._engine_vg_id,
                                                                 self.engine_key)
        if with_group:
            if e_vg.has_single_voice:
                label = (f'{self.voice_label},  {e_vg.lang_tag}, '
                         f'{self.voice_quality_label} Quality')
            else:
                label = (f'{e_vg.vg_name} / {self.voice_label},  '
                         f'({len(e_vg.voices)} Voices {e_vg.lang_tag}), '
                         f'{self.voice_quality_label} Quality')
        else:
            label = f'Voice: {self.voice_label}'

        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'{label}')
        return label

    @property
    def cache_path_segment(self) -> Path:
        if self._cache_path_segment is None:
            self._cache_path_segment = Path(self._lang.to_tag().lower())
        return self._cache_path_segment

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
        interpreation of the uid can be performed. So if, for example, voice_quality,
        makes no difference in identifying the voice, then it can be ommitted or
        ignored.
        """
        # MY_LOGGER.debug(f'voice_uid: {self._voice_uid}')
        if self._voice_uid is None:
            self._voice_uid = (f'{self.engine_key}|{self.engine_vg_id}|'
                               f'{self.e_voice_id}')
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'voice_uid is now {self._voice_uid}')
        return self._voice_uid

    @classmethod
    def get_instance_for_key(cls, voice_key: str) -> 'EngineVoice':
        parts: list[str] = voice_key.split('_|_')
        if len(parts) != 2:
            raise ValueError(f'Invalid voice key: {voice_key}')
        engine_id: str = parts[0]
        voice_id: str = parts[1]
        voices_for_engine: 'Dict[str, EngineVoice]'
        voices_for_engine = cls._voice_by_engine.get(engine_id)
        if voices_for_engine is None:
            raise ValueError(f'Invalid voice key: {voice_key}')
        voice: EngineVoice = voices_for_engine[voice_id]
        return voice

    @property
    def gender_label(self) -> str | None:
        if self._gender_label is None:
            self._gender_label = self.gender.label
        return self._gender_label

    def __eq__(self, other) -> bool:
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        if isinstance(other, EngineVoice):
            other: EngineVoice
            return self.uid == other.uid
            #  return (self.engine_key == other.engine_key and
            #          self.engine_voice == other.engine_voice)
        return False

    def __hash__(self) -> int:
        return hash(self.uid)

    def __repr__(self) -> str:
        if not MY_LOGGER.isEnabledFor(DEBUG):
            return ''
        field_sep: str = ''
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            result = f'EV label: {self.voice_label} e_v_id: {self.e_voice_id}'
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            gender_str: str = f'   gender: {self.gender}{field_sep}'
            vg_id_str: str = f' vg_id: {self.engine_vg_id}{field_sep}'
            voice_quality_str: str = (f'   vg_quality: {self.voice_quality}'
                                      f'{field_sep} ')
            translated_gender_name_str: str = (f'   gender_label: '
                                               f'{self.gender_label}{field_sep}')
            uid_str: str = f'uid: {self.uid}'
            result = (f'EngineVoice: '
                      f'{vg_id_str}'
                      f'{gender_str}'
                      f'{voice_quality_str} {translated_gender_name_str} {uid_str}')
        return result
