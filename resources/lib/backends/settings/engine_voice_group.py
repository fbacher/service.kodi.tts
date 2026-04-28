# coding=utf-8
from __future__ import annotations

from backends.settings.i_engine_voice import IEngineVoice
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from backends.settings.lang_utils import LangUtils
from common.settings import Settings

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


class EngineVoiceGroup(IEngineVoiceGroup):
    """
    Voice Groups are defined at startup, in bootstrap_engines,
    BEFORE the engines are fully defined. During configuration, EngineVoiceGroup
    should only 'inhale' the voice information during settings definition
    and not query other engines during this stage.
    """

    initialized: bool = False
    _, _, _, kodi_language = LangUtils.get_kodi_locale_info()
    kodi_language: Language

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
    vg_by_engine: Dict[ServiceID, Dict[str, List[ForwardRef('EngineVoiceGroup')]]] = {}

    # vg_keys: Dict[str, EngineVoiceGroup] = {}
    # Lookup table for EngineVoiceGroup instances
    # Key is provided by get_key()
    vg_keys: Dict[str, EngineVoiceGroup] = {}

    def __init__(self, engine_key: ServiceID,
                 lang: Language,
                 gender: Genders,
                 default_voice_id: str,
                 engine_lang_id: str,
                 engine_vg_id: str,
                 voice_quality: QualityType,
                 vg_name: str = None,
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
        :param vg_name: Names the collection that a voice
                                   belongs.
        :param locale_match: Measure of how much THIS lang's locale differs from the
                             current Kodi locale. (Using langcodes.tag_distance).
                             Gives some vague hint it how much the langs may differ
                             in speech.
        """
        clz = EngineVoiceGroup
        self._engine_key = engine_key
        self._gender: Genders = gender
        self._default_voice_id: str = default_voice_id
        self._full_vg_label: str | None = None
        self._lang: Language = lang
        self._engine_lang_id: str = engine_lang_id
        self._engine_vg_id: str = engine_vg_id
        self._voice_quality: QualityType = voice_quality
        self._vg_name: str = vg_name
        self._vg_label: str | None = None
        if locale_match < 0:
            locale_match = clz.kodi_language.distance(supported=lang)
        self._locale_match: int = locale_match

        # Voices indexed by engine_voice id
        self._voices: Dict[str, ForwardRef('EngineVoice')] = {}
        """
            label: Translated label in the format of:
                     f'voice_group:  {vg_name:20}')
            prepare_for_display fills it in
        """
        self._gender_label: str | None = None
        self._vg_uid: str | None = None

        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'{self}')
        vg_by_locale: Dict[str, List[ForwardRef('EngineVoiceGroup')]]
        vg_by_locale = clz.vg_by_engine.setdefault(engine_key, {})
        vgs_in_locale: List[ForwardRef('EngineVoiceGroup')]
        locale_id: str = lang.to_tag()  # .lower()
        vgs_in_locale = vg_by_locale.setdefault(locale_id, [])
        vgs_in_locale.append(self)

    @property
    def uid(self) -> str:
        """
            Unique id for the voice group
        """
        if self._vg_uid is None:
            self._vg_uid = ServiceID.get_uid(self._engine_key, self._engine_vg_id)
        return self._vg_uid

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def gender(self) -> Genders:
        return self._gender

    @property
    def default_voice_id(self) -> str:
        return self._default_voice_id

    @property
    def lang(self) -> Language:
        return self._lang

    @property
    def lang_tag(self) -> str:
        """
        Gets the Language.tag for the language-territory
        ex. 'en-US'
        """
        return self._lang.to_tag()

    @property
    def engine_lang_id(self) -> str:
        return self._engine_lang_id

    @property
    def engine_vg_id(self) -> str:
        return self._engine_vg_id

    @property
    def voice_quality(self) -> QualityType:
        return self._voice_quality

    @property
    def voice_quality_label(self) -> str:
        return self._voice_quality.label

    @property
    def vg_name(self) -> str:
        return self._vg_name

    @property
    def e_voices(self) -> Dict[str, ForwardRef('EngineVoice')]:
        """
        :returns: a dictionary[engine_voice, EngineVoice]
        """
        return self._voices

    @property
    def default_e_voice(self) -> ForwardRef('EngineVoice'):
        """
        Default voice of the group
        """
        try:
            return self._voices[self._default_voice_id]
        except KeyError:
            MY_LOGGER.exception('')
            MY_LOGGER.debug(f'{self}')

    @property
    def locale_match(self) -> int:
        return self._locale_match

    def add_voice(self, voice: ForwardRef('EngineVoice')) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'Adding voice at idx: {voice.e_voice_id} type: '
                               f'type: {type(voice.e_voice_id)}')
        self._voices[voice.e_voice_id] = voice

    @property
    def has_single_voice(self) -> bool:
        """
        A voice-group can have multiple voices. When there is a single voice,
        the voice-group is treated as just a voice. A SelectionDialog either
        presents a list of EngineVoiceGroups to choose from, or voices.
        """
        return len(self._voices) == 1

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
        if engine_key is None:
            engine_key = Settings.get_engine_key()
        if locale is None:
            locale = Settings.get_language(engine_key)
        if vg_id is None:
            vg_id = Settings.get_voice_id(engine_key)
        """
        vg_by_engine: key: ServiceID
                        value: Dict[ietf_tag, List[EngineVoiceGroup]]
                        ietf-tag ('en-us')
                        List[EngineVoiceGroup} list of all vgs supported by 
                        that engine and locale_id/ietf-tag ('en-us')
        """

        vgs_by_locale: Dict[str, List[ForwardRef('EngineVoiceGroup')]]
        vgs_by_locale = cls.vg_by_engine.get(engine_key)
        MY_LOGGER.debug(f'vgs_by_locale: {vgs_by_locale}')
        vgs: List[EngineVoiceGroup] = vgs_by_locale.get(locale)

        MY_LOGGER.debug(f'{engine_key} locale: {locale} vg_id: {vg_id}')
        MY_LOGGER.debug(f'vgs: {vgs}')
        for vg in vgs:
            if vg._engine_vg_id == vg_id:
                return vg
        return None

    @property
    def gender_label(self) -> str:
        if self._gender_label is None:
            self._gender_label = self.gender.label
        return self._gender_label


    @property
    def vg_label(self) -> str:
        """
        Gets the label for this voice group

        :return: Only the Voice Group's label (
        """
        return self._vg_label

    def full_vg_label(self, voice_id: str) -> str:
        """
        Inclues Voice Group's label, if any.

        :param voice_id: Index into self.voices for the selected/default voice
        :return: The Voice_Group's label along with the Voice label
        """
        # KEEP IN SYNC WITH EngineVoice.full_voice_label

        e_voice: IEngineVoice = self.voices[voice_id]
        if self.has_single_voice:
            label = (f'{e_voice.voice_label},  {self.lang_tag}, '
                     f'{self.voice_quality.label} Quality')
        else:
            label = (f'{self.vg_name} / {e_voice.voice_label}  '
                     f'({len(self.voices)} Voices), {self.lang_tag}, '
                     f'{self.voice_quality.label} Quality')
        return f'{label}'

    @property
    def vg_uid(self) -> str:
        #  TODO: Belongs in voices
        return self._vg_uid

    def __repr__(self) -> str:

        if not MY_LOGGER.isEnabledFor(DEBUG):
            return ''
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            result = f'EVG: {self.vg_name}'
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            field_sep: str = ''  # '{field_sep}'
            engine_key_str = f'   eng: {self.engine_key} '
            voice_str: str = f'   voice: {self.vg_name}{field_sep}'
            engine_vg_id_str: str = (f'   e_vg_id: '
                                     f'{self.engine_vg_id}{field_sep}')
            vg_quality_str: str = f'   vg_quality: {self.voice_quality}{field_sep} '
            gender_label_str: str = (f'   gender_label: '
                                     f'{self.gender_label}{field_sep}')
            result = (f'{result}\n'
                      f'{engine_key_str}'
                      f'{engine_vg_id_str} '
                      f'{voice_str}'
                      f'{vg_quality_str} {gender_label_str}')
        return result

    @property
    def voices(self):
        return self._voices
