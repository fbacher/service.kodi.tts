# coding=utf-8
"""
Module responsible for discovering, organizing the voice and language capabilities
of the various engines.
"""
from __future__ import annotations

from pathlib import Path

from backends.settings.i_engine_lang import IEngineLang
from backends.settings.i_engine_voice import IEngineVoice
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from backends.settings.service_types import (QualityType, ServiceID)
from typing import Any, Dict, Final, ForwardRef, List, Tuple, Union

from common.logger import *
from common.setting_constants import Genders

MY_LOGGER = BasicLogger.get_logger(__name__)


class IEngineVoiceManager:

    e_v_m: 'Union[IEngineVoiceManager, None]' = None

    '''
    # Engine's ServiceID gives Dict[ietf_tag] of it's language
    engine_langs: Dict[ServiceID, Dict[str, EngineLang]] = {}

    # lang_uid (see get_uid()) gives it's language
    engine_lang_by_uid: Dict[str, EngineLang] = {}

    # Engine's ServiceID gives Dict[vg_id] of all of its VoiceGroups
    engine_vgs: Dict[ServiceID, Dict[str, EngineVoiceGroup]] = {}

    # Get VoiceGroups by engine, locale
    vgs_by_engine_locale: Dict[ServiceID, Dict[str, List[EngineVoiceGroup]]] = {}

    # voice_group_uid (see get_uid()) gives its voice_group
    vgs_by_uid: Dict[str, EngineVoiceGroup] = {}

    # Engine's ServiceID gives Dict[voice_id] of all of it's voices
    engine_voices: Dict[ServiceID, Dict[str, EngineVoice]] = {}

    # voice_uid (see get_uid()) gives a voice
    voice_by_uid: Dict[str, EngineVoice] = {}

    initialized: bool = False
    all_languages_loaded: bool = False
    '''

    @classmethod
    def init(cls):
        return cls.e_v_m.init()

    @classmethod
    def discover(cls) -> None:
        """
        Discover the language and voicing capabilities of the engines.

        Causes engines to populate engine_language and engine_voice instances
        """
        return cls.e_v_m.discover()

    @classmethod
    def get_e_voice(cls, engine_key: Union[ServiceID, None] = None) -> IEngineVoice:
        return cls.e_v_m.get_e_voice(engine_key)

    @classmethod
    def set_e_voice(cls, e_voice: IEngineVoice) -> None:
        return cls.e_v_m.set_e_voice(e_voice)

    @classmethod
    def add_language(cls, engine_key: ServiceID, ietf_tag: str,
                     engine_lang_id: str) -> IEngineLang:
        """
        Adds a language to the engine's language list

        :param engine_key: ServiceID id for an engine
        :param ietf_tag: langcodes.Language.ietf.to_tag() tag i.e. 'en-US'
        :param engine_lang_id: engine's code for this language

        """
        return cls.e_v_m.add_language(engine_key, ietf_tag, engine_lang_id)

    @classmethod
    def get_eng_lang_by_uid(cls, uid: str) -> IEngineLang | None:
        return cls.e_v_m.engine_lang_by_uid.get(uid)

    @classmethod
    def get_eng_langs_for_engine(cls, engine_key: ServiceID) -> Dict[str, IEngineLang]:
        return cls.e_v_m.get_eng_langs_for_engine(engine_key)

    @classmethod
    def get_eng_voice_by_uid(cls, uid: str) -> IEngineVoice | None:
        return cls.e_v_m.get_eng_voice_by_uid(uid)

    @classmethod
    def add_voice_group(cls,
                        engine_key: ServiceID,
                        ietf_tag: str,
                        gender: Genders,
                        default_voice_id: str,
                        engine_lang_id: str,
                        engine_vg_id: str,
                        voice_quality: QualityType,
                        vg_label: str = None) -> ForwardRef('IEngineVoiceGroup'):
        """
        Defines a Voice Group.

        Some Engines have groups of voices, such as Piper. In Piper's case
        the voices that are a member of a Voice Group share the parameters
        defining the voice, except for a very small number. This allows switching
        between the different voices in a group to be very cheap compared to loading
        completely new voices.

        :param engine_key: ServiceID id for an engine
        :param ietf_tag: defines the locale of the voice. Use
                         langcodes.Language.ietf.to_tag() tag i.e. 'en-US'
        :param gender: defines the gender of the voice.
        :param default_voice_id: defines the default voice for the group
        :param engine_lang_id: specifies the engine-specific code to use for using
                         this voicegroup or one of the voices contained in it
        :param engine_vg_id: engine-specific code for the voice-group id.
        :param voice_quality: defines the voice quality of the voice. Zero is best.
        :param vg_label: defines the label of this voice-group.
        """
        return cls.e_v_m.add_voice_group(engine_key, ietf_tag, gender,
                                         default_voice_id,
                                         engine_lang_id,
                                         engine_vg_id,
                                         voice_quality,
                                         vg_label)

    @classmethod
    def add_voice(cls,
                  engine_key: ServiceID,
                  ietf_tag: str,
                  gender: Genders,
                  engine_lang_id: str,
                  e_voice_id: str,
                  engine_vg_id: str | None,
                  voice_quality: QualityType,
                  voice_label: str = None,
                  cache_path_segment: Path | None = None) -> IEngineVoice:
        """
        Defines a Voice, which may or may not be a member of a voice group.
        Automatically adds a voice group if engine_vg_id is defined and
        voice-group does not already exist. Use add_voice_group to explicitly
        add a voice-group.

        :param engine_key: ServiceID id for an engine
        :param ietf_tag: defines the locale of the voice. Use
                         langcodes.Language.ietf.to_tag() tag i.e. 'en-US'
        :param gender: defines the gender of the voice.
        :param engine_lang_id: specifies the engine-specific code to use for using
                         this voicegroup or one of the voices contained in it
        :param e_voice_id: engine-specific code for the voice
        :param engine_vg_id: engine-specific code for the voice-group id that
                            this voice is associated with. None if not
                            associated.
        :param voice_quality: defines the voice quality of the voice. Zero is best.
        :param cache_path_segment: Engine-specific portion of cache path that
               is unique for the particular voice being used. Typicaly a concise
               representation of <vg_id>-<voice_id>. Default value is
               vg_id-voice_id
        :param voice_label: defines the label of this voice. Combined with Voice Group
                            label, as needed.

        Note: When VoiceGroup is created by this function:
          The voice groups':
              vg_label is set to voice_label.
              voice_id is set to engine_voice
              engine_key,lang, gender, engine_lang_id, engine_vg_id are all set
              to the voice's value.
          The VoiceGroup is created when first Voice is added, so all above values
          are taken from the FIRST voice added for that group.

        """
        return cls.e_v_m.add_voice(engine_key, ietf_tag, gender,
                                   engine_lang_id,
                                   e_voice_id,
                                   engine_vg_id,
                                   voice_quality,
                                   voice_label,
                                   cache_path_segment)

    @classmethod
    def get_vgs_by_locale(cls, engine_key: ServiceID) -> (
            'Dict[str, List[EngineVoiceGroup]]'):
        """
        Gets voice-groups supported by a TTS engine, grouped by locale

        :param engine_key: engine to get voices for

        :return: Dict indexed by <ietf.to_tag()> Values are lists of voices
        """
        return cls.e_v_m.get_vgs_by_locale(engine_key)

    @classmethod
    def get_vg(cls, vg_id: str, service_id: ServiceID) -> IEngineVoiceGroup:
        return cls.e_v_m.get_vg(vg_id, service_id)

    @classmethod
    def get_vg_label(cls, vg_uid: str) -> str:
        """
        Gets the label from the VoiceGroup identified by vg_uid, UNLESS the
        VoiceGroup is a dummy (VoiceGroup only contains one Voice), where empty
        string is returned.

        :param vg_uid: VoiceGroup identifier
        :return: Label for the VoiceGroup, or empty string if a dummy VoiceGroup
        """
        return cls.e_v_m.get_vg_label(vg_uid)
