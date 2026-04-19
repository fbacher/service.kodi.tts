# coding=utf-8
"""
Module responsible for discovering, organizing the voice and language capabilities
of the various engines.
"""
from pathlib import Path

from backends.settings.engine_lang import EngineLang
from backends.settings.engine_voice import EngineVoice
from backends.settings.i_engine_voice_group import IEngineVoiceGroup
from backends.settings.i_engine_voice_manager import IEngineVoiceManager
from backends.settings.service_types import (EngineType, QualityType, ServiceID,
                                             ServiceType)
from typing import Any, Dict, Final, ForwardRef, List, Tuple

from common.settings import Settings
from langcodes import Language

from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.service_unavailable_exception import ServiceUnavailable
from backends.settings.settings_map import SettingsMap
from common.base_services import BaseServices
from common.logger import *
from common.setting_constants import Genders

MY_LOGGER = BasicLogger.get_logger(__name__)


class EngineVoiceManager(IEngineVoiceManager):

    # Engine's ServiceID gives Dict[ietf_tag] of it's language
    engine_langs: Dict[ServiceID, Dict[str, EngineLang]] = {}

    # lang_uid (see get_uid()) gives it's language
    engine_lang_by_uid: Dict[str, EngineLang] = {}

    # Engine's ServiceID gives Dict[vg_id] of all of its VoiceGroups
    engine_vg_by_engine_id: Dict[ServiceID, Dict[str, EngineVoiceGroup]] = {}

    # Get VoiceGroups by engine, locale (ietf.to_tag())
    # TODO: May not be used properly
    vgs_by_engine_locale: Dict[ServiceID, Dict[str, List[EngineVoiceGroup]]] = {}

    # voice_group_uid (see get_uid()) gives its voice_group
    vg_by_uid: Dict[str, EngineVoiceGroup] = {}

    # Engine's ServiceID gives Dict[voice_id] of all of it's voices
    engine_voices: Dict[ServiceID, Dict[str, EngineVoice]] = {}

    # voice_uid (see get_uid()) gives a voice
    voice_by_uid: Dict[str, EngineVoice] = {}

    initialized: bool = False
    all_languages_loaded: bool = False

    @classmethod
    def init(cls):
        if cls.initialized:
            return
        IEngineVoiceManager.e_v_m = cls
        cls.initialized = True

    @classmethod
    def discover(cls) -> None:
        """
        Discover the language and voicing capabilities of the engines.

        Causes engines to populate engine_language and engine_voice instances
        """
        if cls.all_languages_loaded:
            return
        EngineLang.init()
        avail_engines: List[ServiceID]
        avail_engines = SettingsMap.get_available_services(ServiceType.ENGINE)

        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'discover_lang_info engine_keys: {len(avail_engines)}')
        failure: bool = False
        for engine_key in reversed(avail_engines):
            engine_key: ServiceID

            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'getting lang for {engine_key}')
            try:
                new_active_engine = BaseServices.get_service(engine_key)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'active_engine: {new_active_engine}')
                if new_active_engine is None:
                    failure = True
                    continue
                new_active_engine.load_voices()
            except ServiceUnavailable:
                MY_LOGGER.exception(f'Error getting languages from {engine_key}.'
                                    f' Skipping')
            except Exception:
                MY_LOGGER.exception(f'Error getting languages from {engine_key}.'
                                    f' Skipping')
        if not failure:
            cls.all_languages_loaded = True
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'Returned from load_voices()')

    @classmethod
    def get_e_voice(cls, engine_key: ServiceID | None = None) -> EngineVoice:
        """
            Gets the current voice setting for the given engine_key
        """
        if engine_key is None:
            engine_key: ServiceID = Settings.get_engine_key()
        # MY_LOGGER.debug(f'engine_key: {engine_key}')
        raw_voice_id: str = Settings.get_voice_id(engine_key)
        # MY_LOGGER.debug(f'raw_voice_id: {raw_voice_id}')
        # MY_LOGGER.debug(f'voice_by_uid: '
        #                 f'{"\n".join(EngineVoiceManager.voice_by_uid.keys())}')
        e_voice: EngineVoice = EngineVoiceManager.voice_by_uid.get(raw_voice_id)
        if e_voice is None:
            MY_LOGGER.debug(f'Voice is BAD')

        return e_voice

    @classmethod
    def set_voice(cls, e_voice: EngineVoice) -> None:
        engine_key: ServiceID = e_voice.engine_key
        raw_voice_id: str = e_voice.uid
        MY_LOGGER.debug(f'engine_key: {engine_key} raw_voice_id: {raw_voice_id}')

        Settings.set_voice(raw_voice_id, engine_key)

    @classmethod
    def add_language(cls, engine_key: ServiceID, ietf_tag: str,
                     engine_lang_id: str) -> EngineLang:
        """
        Adds a language to the engine's language list

        :param engine_key: ServiceID id for an engine
        :param ietf_tag: langcodes.Language.ietf.to_tag() tag i.e. 'en-US'
        :param engine_lang_id: engine's code for this language

        """
        eng_lang: EngineLang
        uid: str = ServiceID.get_uid(engine_key, ietf_tag)
        eng_lang = cls.engine_lang_by_uid.get(uid)
        if eng_lang is not None:
            return eng_lang

        ietf_lang: Language = Language.get(ietf_tag)
        lang: EngineLang
        lang = EngineLang(engine_key, ietf_lang, engine_lang_id)

        # Engine's ServiceID gives Dict[ietf_tag] of its language
        # cls.engine_langs: Dict[ServiceID, Dict[str, EngineLang]]
        langs_for_engine: Dict[str, EngineLang]
        langs_for_engine = cls.engine_langs.setdefault(engine_key, {})
        langs_for_engine[ietf_tag] = lang

        # lang_uid (see get_uid()) gives it's language
        lang_uid: str = ServiceID.get_uid(engine_key, ietf_tag)
        if lang_uid not in cls.engine_lang_by_uid.keys():
            cls.engine_lang_by_uid[lang_uid] = lang
        MY_LOGGER.debug(f'Adding language {ietf_tag} to {engine_key}')
        MY_LOGGER.debug(f'cls.lang_by_uid: {cls.engine_lang_by_uid.keys()}')
        return lang

    @classmethod
    def get_eng_lang_by_uid(cls, uid: str) -> EngineLang | None:
        return cls.engine_lang_by_uid.get(uid)

    @classmethod
    def get_eng_langs_for_engine(cls, engine_key: ServiceID) -> Dict[str, EngineLang]:
        langs_for_engine: Dict[str, EngineLang]
        langs_for_engine = cls.engine_langs.setdefault(engine_key, {})
        return langs_for_engine

    @classmethod
    def get_eng_voice_by_uid(cls, uid: str) -> EngineVoice | None:
        return cls.voice_by_uid.get(uid)

    @classmethod
    def add_voice_group(cls,
                        engine_key: ServiceID,
                        ietf_tag: str,
                        gender: Genders,
                        default_voice_id: str,
                        engine_lang_id: str,
                        engine_vg_id: str,
                        voice_quality: QualityType,
                        voice_quality_label: str = '',
                        vg_label: str = None) -> EngineVoiceGroup:
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
        :param voice_quality_label: User-friendly label for the voice quality
        :param vg_label: defines the label of this voice-group.
        """
        vg_uid: str = ServiceID.get_uid(engine_key, engine_vg_id)
        vg: EngineVoiceGroup = cls.vg_by_uid.get(vg_uid)
        if vg is not None:
            return vg

        lang: Language = Language(ietf_tag)
        vg: EngineVoiceGroup = EngineVoiceGroup(engine_key=engine_key,
                                                lang=lang,
                                                gender=gender,
                                                default_voice_id=default_voice_id,
                                                engine_lang_id=engine_lang_id,
                                                engine_vg_id=engine_vg_id,
                                                voice_quality=voice_quality,
                                                voice_quality_label=voice_quality_label,
                                                vg_name=vg_label)
        cls.vg_by_uid[vg.uid] = vg
        engine_vgs: Dict[str, EngineVoiceGroup]
        engine_vgs = cls.engine_vg_by_engine_id.setdefault(engine_key, {})
        engine_vgs[engine_vg_id] = vg

        vgs_by_locale: Dict[str, List[EngineVoiceGroup]]
        vgs_by_locale = cls.vgs_by_engine_locale.setdefault(engine_key, {})
        vgs: List[EngineVoiceGroup] = vgs_by_locale.setdefault(lang.to_tag(), [])
        vgs.append(vg)
        MY_LOGGER.debug(f'Added {engine_key} to vgs_by_locale: locale:'
                        f' {lang.to_tag()} vg: {vg}')
        return vg

    @classmethod
    def add_voice(cls,
                  engine_key: ServiceID,
                  ietf_tag: str,
                  gender: Genders,
                  engine_lang_id: str,
                  e_voice_id: str,
                  engine_vg_id: str | None,
                  voice_quality: QualityType,
                  voice_quality_label: str = '',
                  voice_label: str = None,
                  cache_path_segment: Path | None = None,) -> EngineVoice:
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
        :param voice_quality_label: User-friendly label for the voice quality
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
        MY_LOGGER.debug(f'engine: {engine_key} locale: {ietf_tag}')
        lang: Language = Language(ietf_tag)
        # engine_vgs: Dict[str, EngineVoiceGroup]
        # engine_vgs = cls.engine_vgs.setdefault(engine_key, {})
        # engine_vgs[engine_vg_id] = vg
        vg_uid: str = ServiceID.get_uid(engine_key, engine_vg_id)
        MY_LOGGER.debug(f'vg_uid: {vg_uid}')
        vg: EngineVoiceGroup
        vg = cls.vg_by_uid.get(vg_uid)
        MY_LOGGER.debug(f'vg: {vg}')
        if vg is None:
            MY_LOGGER.debug(f'Adding voice group for voice vg_uid: {vg_uid}')
            vg = cls.add_voice_group(engine_key=engine_key,
                                     ietf_tag=ietf_tag,
                                     gender=gender,
                                     default_voice_id=e_voice_id,
                                     engine_lang_id=engine_lang_id,
                                     engine_vg_id=engine_vg_id,
                                     voice_quality=voice_quality,
                                     voice_quality_label=voice_quality_label,
                                     vg_label=voice_label)

        ev: EngineVoice = cls.voice_by_uid.get(e_voice_id)
        if ev is not None and ev in vg.e_voices:
            MY_LOGGER.debug(f'Voice already exists in VoiceGroup '
                            f'ev_id: {e_voice_id}')
            return ev

        e_voice: EngineVoice = EngineVoice(engine_key=engine_key,
                                           lang=lang,
                                           gender=gender,
                                           engine_lang_id=engine_lang_id,
                                           e_voice_id=e_voice_id,
                                           engine_vg_id=engine_vg_id,
                                           voice_quality=voice_quality,
                                           voice_quality_label=voice_quality_label,
                                           voice_label=voice_label,
                                           cache_path_segment=cache_path_segment)
        MY_LOGGER.debug(f'Adding voice vg: {vg} e_voice: {e_voice}')
        vg.add_voice(e_voice)
        voice_by_id: Dict[str, EngineVoice]
        voice_by_id = cls.engine_voices.setdefault(engine_key, {})
        voice_by_id[e_voice_id] = e_voice

        # voice_uid (see get_uid()) gives a voice
        cls.voice_by_uid[e_voice.uid] = e_voice
        return e_voice

    @classmethod
    def get_vgs_by_locale(cls, engine_key: ServiceID) -> (
            Dict[str, List[ForwardRef('EngineVoiceGroup')]]):
        """
        Gets voice-groups supported by a TTS engine, grouped by locale

        :param engine_key: engine to get voices for

        :return: Dict indexed by <ietf.to_tag()> Values are lists of voices
        """
        MY_LOGGER.debug(f'engine_key: {engine_key}')
        vgs_by_locale: Dict[str, List[EngineVoiceGroup]]
        vgs_by_locale = cls.vgs_by_engine_locale.get(engine_key, {})
        return vgs_by_locale

    @classmethod
    def get_vg(cls, vg_id: str, service_id: ServiceID) -> IEngineVoiceGroup:
        vgs_for_service: Dict[str, EngineVoiceGroup]
        vgs_for_service = cls.engine_vg_by_engine_id.get(service_id)
        if vgs_for_service is None:
            raise ValueError(f'No VoiceGroups in service: {service_id} vg_id {vg_id}')
        vg: IEngineVoiceGroup
        vg = vgs_for_service.get(vg_id)
        if vg is None:
            raise ValueError(f'No VoiceGroup with vg_id: {vg_id} for {service_id}')
        return vg

    @classmethod
    def get_vg_label(cls, vg_uid: str) -> str:
        """
        Gets the label from the VoiceGroup identified by vg_uid, UNLESS the
        VoiceGroup is a dummy (VoiceGroup only contains one Voice), where empty
        string is returned.

        :param vg_uid: VoiceGroup identifier
        :return: Label for the VoiceGroup, or empty string if a dummy VoiceGroup
        """
        e_vg = EngineVoiceGroup = cls.vg_by_uid[vg_uid]
        if len(e_vg.e_voices) == 1:
            return ''
        return e_vg.vg_name


EngineVoiceManager.init()
