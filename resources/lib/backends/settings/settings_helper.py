# coding=utf-8
from __future__ import annotations

from collections import UserList

from backends.settings.engine_lang import EngineLang
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.engine_voice_manager import EngineVoiceManager
from langcodes import Language
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import (ALL_ENGINES, ALL_PLAYERS, EngineType,
                                             PlayerType, QualityType, ServiceID,
                                             ServiceKey)
try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Dict, ForwardRef, List, Tuple, Union

from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.i_validators import AllowedValue, IStringValidator
from backends.settings.service_types import ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import StringValidator
from common.logger import *
from common.setting_constants import PlayerMode
from common.settings import Settings
from windowNavigation.choice import (Choice, ChoiceDict, Choices, EngineChoice,
                                     EngineChoices,
                                     VGChoice, VGChoices, VoiceChoice, VoiceChoices)

MY_LOGGER = BasicLogger.get_logger(__name__)


class FormatType(StrEnum):
    """
    Indicates how to format the names of language choices.

    Format may depend upon the engine used. For example, GoogleTTS does not
    have voice names, the language and country determine that. However, eSpeak
    uses voice names that can't quite map to variant names.
    """
    DISPLAY = 'display_name'
    SHORT = 'short'
    LONG = 'long'


class SettingsHelper:
    engine_id: str = None
    engine_instance: ITTSBackendBase | None = None
    allowed_player_modes: Dict[str, List[AllowedValue]] = {}
    _, _, _, kodi_language = LangUtils.get_kodi_locale_info()
    kodi_language: Language

    @classmethod
    def build_allowed_player_modes(cls) -> None:
        """
           Creates a Dictionary of the allowed PlayerModes for a given service.

           The created structure is allowed_player_modes

           The engine and player_key must both support the same PlayerMode. The UI
           needs to reflect what the current choices are. Side-effects that
           lead to incorrect configurations must be prevented.

           The structure is simple. It is indexed by setting_id (engine or
           player_key). Each value is a list of AllowedValues for PlayerMode for
           that service. The structure is used to see if a combination of
           engine, player_key and mode are valid. AllowedValue has an enabled
           flag that is False when that PlayerMode can not be used due to
           that other service (engine or player_key) involved.

           Use Cases:
              The UI allows the user to select the Engine, Player and PlayerMode
              independently. However, they all depend upon each other. When a
              change is made that creats an invalid configuration it is much
              better to automatically adjust the configuration so that it
              remains valid rather than going through a cumbersome multi-step
              process to manually make the changes.

              Related to the first case. The user desires to hear the effects
              of the change while making them.
        """
        # if len(cls.allowed_player_modes.keys()) > 0:
        #     return

        for service_type, services in [(ServiceType.ENGINE, ALL_ENGINES),
                                       (ServiceType.PLAYER, ALL_PLAYERS)]:
            service_type: ServiceType
            services: List[EngineType | PlayerType]
            for service in services:
                service: EngineType | PlayerType
                service_key: ServiceID = ServiceID(service_type, service)
                if not SettingsMap.is_available(service_key):
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'service NOT available: {service_key}')
                    continue
                player_mode_key: ServiceID
                player_mode_key = service_key.with_prop(SettingProp.PLAYER_MODE)
                player_mode_val: StringValidator | IStringValidator
                player_mode_val = SettingsMap.get_validator(player_mode_key)
                if player_mode_val is None:
                    MY_LOGGER.info(f'No PLAYER_MODE validator for: {player_mode_key}')
                    continue
                allowed_player_modes: List[AllowedValue]
                allowed_player_modes = player_mode_val.get_allowed_values()
                #  MY_LOGGER.debug(f'service: {player_mode_key} allowed_modes: '
                #                  f'{allowed_player_modes}')
                cls.allowed_player_modes[f'{player_mode_key}'] = allowed_player_modes

    @classmethod
    def get_valid_player_modes(cls, engine_key: ServiceID, player: PlayerType,
                               player_mode: PlayerMode
                               ) -> Tuple[List[PlayerMode], int]:
        """
        Determines which player_modes are common to both the given engine
        and player_key and the index into that list to the given player_mode

        :param engine_key:  The engine to be used
        :param player: The player to be used
        :param player_mode: The proposed player_key mode
        :return: Tuple[List[AllowedValue], int]
                 List of intersecting player_modes and the index to the element
                 equal to the given player_mode, or -1 if not found.
        """
        # TODO: Consider adding AllowedValue and Choice wrappers at a higher level

        player_player_mode_key: ServiceID = ServiceID(ServiceType.PLAYER, player,
                                                      SettingProp.PLAYER_MODE)
        engine_player_mode_key: ServiceID = engine_key.with_prop(SettingProp.PLAYER_MODE)
        #  MY_LOGGER.debug(f'engine_key: {engine_key} '
        #                  f'engine_player_mode_key: {engine_player_mode_key}')
        #  MY_LOGGER.debug(f'player_player_mode_key: {player_player_mode_key}')
        #  MY_LOGGER.debug(f'allowed_player_modes: {cls.allowed_player_modes}')
        engine_allowed_values: List[AllowedValue]
        engine_allowed_values = cls.allowed_player_modes.get(f'{engine_player_mode_key}',
                                                             [])
        player_allowed_values: List[AllowedValue]
        player_allowed_values = cls.allowed_player_modes.get(f'{player_player_mode_key}',
                                                             [])
        engine_player_modes: List[PlayerMode] = []
        player_player_modes: List[PlayerMode] = []

        # AllowedValues are UI oriented. All possible player_modes for engine or
        # player_key are returned, with the ones valid for that player_key or engine
        # marked as enabled. Convert into a simple list of the allowed player_modes
        # for each. (TODO Simplify)

        for allowed_value in engine_allowed_values:
            allowed_value: AllowedValue
            #  MY_LOGGER.debug(f'playerMode: {allowed_value}')
            if allowed_value.enabled:
                value: PlayerMode = PlayerMode(allowed_value.value)
                #  MY_LOGGER.debug(f'value: {value} type: {type(value)}')
                engine_player_modes.append(value)
        for allowed_value in player_allowed_values:
            allowed_value: AllowedValue
            #  MY_LOGGER.debug(f'playerMode2: {allowed_value}')
            if allowed_value.enabled:
                value: PlayerMode = PlayerMode(allowed_value.value)
                #  MY_LOGGER.debug(f'value2: {value} type: {type(value)}')
                player_player_modes.append(value)

        # Now, create list of player_modes that are common to both the engine
        # and player_key
        #  MY_LOGGER.debug(f'engine_player_modes: {engine_player_modes}')
        #  MY_LOGGER.debug(f'player_player_modes: {player_player_modes}')
        intersection: List[PlayerMode] = PlayerMode.intersection(engine_player_modes,
                                                                 player_player_modes)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'intersection: {intersection}')
        # Determine if the preferred player_mode is in this intersection
        idx: int = -1
        try:
            idx = intersection.index(player_mode)
        except ValueError:
            pass
        return intersection, idx

    @classmethod
    def get_engine_choices(cls,
                           current_engine_key: ServiceID) -> (
            Tuple[EngineChoices, int, int] | None):
        """
        Constructs a list of TTS engines that are functional for the current
        machine and language.

        If the engine is changed a default vg will be configured. The default
        vg is either a previously used one, or one of the 'best' voice_groups for that
        engine.

        :param current_engine_key: id of the currently running engine, or None

        :return: A list of EngineChoices that supports the current language,
                 sorted by engine's Quality. The index to the current engine
                 and best engine are also returned.
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'current_engine_key: {current_engine_key}')

        try:
            e_choices: EngineChoices
            e_choices = ChoiceDict.e_choices_for_engine_id
            if len(e_choices) == 0:
                e_choices = cls._get_engine_choices()
                if e_choices is None:
                    raise ValueError('Could not get EngineChoices')

            engine_choice_idx: int = -1
            if current_engine_key is not None:
                idx: int = 0
                for e_choice in e_choices:
                    e_choice: EngineChoice
                    if e_choice.engine_key == current_engine_key:
                        engine_choice_idx = idx
                        break
                    idx += 1

            best_choice_idx: int = 0
            return e_choices, engine_choice_idx, best_choice_idx
        except Exception as e:
            MY_LOGGER.exception('')
        return None

    @classmethod
    def _get_engine_choices(cls) -> EngineChoices:
        """
        Constructs a list of TTS engines that are functional for the current
        machine and language.

        If the engine is changed a default vg will be configured. The default
        vg is either a previously used one, or one of the 'best' voice_groups for that
        engine.

        :return: A list of EngineChoices that supports the current language,
                 sorted by engine's Quality.
        """
        engine_keys: List[ServiceID] | None
        engine_keys = cls.get_active_engines()

        try:
            # Get the first Voice Group for each engine
            # Get every voice the engine supports for the current language.
            # The list is sorted by Quality, Match-distance, vg_label
            # best_vg_choices: List[VGChoices] = []

            e_choices: EngineChoices = EngineChoices()
            for engine_key in engine_keys:
                engine_key: ServiceID
                engine_type: EngineType = EngineType(engine_key.service_id)

                # Choose the best voice from the 'best' VoiceGroup this engine
                # supports
                MY_LOGGER.debug(f'engine: {engine_key}')
                vg_choices: VGChoices = cls.get_vg_choices(engine_key=engine_key)
                t_vg_choice: VGChoice | None = None
                for vg_choice in vg_choices:
                    t_vg_choice = vg_choice
                    MY_LOGGER.debug(f'vg_choice: {vg_choice.label} choices: '
                                    f'{len(vg_choice.v_choices)}')
                if len(vg_choices.choices) == 0:
                    MY_LOGGER.debug(f'zero choices for {t_vg_choice}')
                    continue
                default_vg_idx: int = vg_choices.default_vg_idx
                default_vg_choice: VGChoice = vg_choices[default_vg_idx]
                default_ev: EngineVoice = default_vg_choice.e_vg.default_e_voice
                MY_LOGGER.debug(f'default_vg_idx: {default_vg_idx}, default_vg_choice:'
                                f' {default_vg_choice.label}')
                MY_LOGGER.debug(f'selected_vg_idx: {vg_choices.selected_vg_idx} '
                                f'{vg_choices[vg_choices.selected_vg_idx].label}')
                engine_choice: EngineChoice
                engine_choice = EngineChoice(label=engine_type.label,
                                             value=engine_type,
                                             choice_index=len(e_choices),
                                             sort_key=f'engine_type',
                                             engine_key=engine_key,
                                             lang=default_vg_choice.e_lang,
                                             voice=default_ev)
                e_choices.append(engine_choice)
            return e_choices
        except Exception as e:
            MY_LOGGER.exception('')
        return None

    @classmethod
    def get_active_engines(cls) -> List[ServiceID]:
        DUMMY_ENGINES = ServiceKey.NO_ENGINE_KEY,
        tmp_engines: List[ServiceID]
        tmp_engines = SettingsMap.get_available_services(ServiceType.ENGINE)
        available_engines: List[ServiceID] = []
        for engine in tmp_engines:
            if engine not in DUMMY_ENGINES:
                available_engines.append(engine)

        return available_engines

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        return EngineLang.get_formatted_lang(lang)

    @classmethod
    def identify_closest_match(cls, sorted_choices: VoiceChoices,
                               kodi_locale: str) -> Tuple[VoiceChoices, int]:
        """
        Given a sorted list of Voices of various language-territories and a single engine,
        identify the closest language and voice match and return
        an index to it. Also adds information from lang_info to the Choices.

        Requires that match information already be set prior to call. See
        sort_engine_langs

        :param sorted_choices:
        :param kodi_locale:
        :return:
        """
        idx: int = 0
        if len(sorted_choices) == 0:
            return sorted_choices, -1
        engine_key: ServiceID = sorted_choices[0].engine_key
        # Mark any entry with the same voice and lang_id as the currently selected one.
        current_e_voice_id: str = Settings.get_voice_id(engine_key)
        current_engine_lang_id: str = Settings.get_language(engine_key)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'engine_key: {engine_key} '
                            f'current_voice: {current_e_voice_id} '
                            f'current_lang_id: {current_engine_lang_id}')

        current_choice_index: int = -1
        closest_match_index: int = -1
        closest_match: int = 10000
        v_choices: VoiceChoices = VoiceChoices()
        for v_choice in sorted_choices:
            v_choice: VoiceChoice
            e_voice: EngineVoice = v_choice.e_voice
            engine_key: ServiceID = v_choice.engine_key
            v_choice.choice_idx = idx
            if v_choice.match_distance < closest_match:
                closest_match = v_choice.match_distance
                closest_match_index = idx

            if current_e_voice_id == e_voice.e_voice_id:
                current_choice_index = idx

            v_choices.append(v_choice)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'{v_choice}')
            idx += 1

        if current_choice_index == -1:
            current_choice_index = closest_match_index
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'choice_idx: {current_choice_index} choice: '
                            f'{v_choices[current_choice_index].lang_info.engine_lang_id} '
                            f'{v_choices[current_choice_index].lang_info.e_voice_id}')
        return v_choices, current_choice_index

    @classmethod
    def get_vg_choices(cls,
                       engine_key: ServiceID | None = None) -> VGChoices:
        """
        An engine supports one or more voice_groups.

        Here we make an EngineVoiceGroup be the container of one or more related
        voices. To the user a "Voice" is either a 'normal' independent voice, or
        one from a group of voices. To choose a voice, the user is presented a
        SelectionDialog with the possible voices AND Voice Groups. To choose a
        simple voice, the user just selects it. To choose a voice that is a member
        of an EngineVoiceGroup, the user first selects the Voice Group, then another
        Selection Dialog will appear with just the Voices in that group.

        :param engine_key: Specifies the TTS engine to configure the language/voice
                         for. A ValueError is thrown if None is passed.
        :return:  supported voice_groups, current_vg_idx, current_voice_idx and
                  voice_idx for the given engine. VoiceGroups sorted by: quality,
                  match_distance between Kodi's locale (i.e. en_GB) and the voice's
                  locale and Voice Group's Label.
        """
        if engine_key is None:
            raise ValueError('engine_key is None')

        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'In get_vg_choices service_key: {engine_key}')

        vg_choices: VGChoices | None = None
        vg_choices = ChoiceDict.vg_choices_for_engine_id.get(engine_key)
        if vg_choices is not None:
            return vg_choices

        all_e_vgs_for_engine: List[EngineVoiceGroup] = []
        best_locale_match: int = 10000
        default_vg_idx: int = -1

        try:
            v_gs_for_a_locale: List[EngineVoiceGroup]
            v_gs_items = EngineVoiceManager.get_vgs_by_locale(engine_key).items()
            for locale, v_gs_for_a_locale in v_gs_items:
                all_e_vgs_for_engine.extend(v_gs_for_a_locale)
                for e_vg in all_e_vgs_for_engine:
                    e_vg: EngineVoiceGroup
                    if MY_LOGGER.isEnabledFor(DEBUG_XV):
                        MY_LOGGER.debug_xv(f'e_vg lang_tag: {e_vg.lang_tag} match: '
                                           f'{e_vg.locale_match} quality:'
                                           f' {e_vg.voice_quality}')
                    locale_match: int = e_vg.locale_match
                    # Less is a closer match to our locale
                    if locale_match < best_locale_match:
                        best_locale_match = locale_match
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'locale: {e_vg.lang_tag} closest: '
                                              f'{best_locale_match}')

        except Exception as e:
            MY_LOGGER.exception('')
        try:
            vg_choice_list: List[VGChoice] = list()

            for e_vg in all_e_vgs_for_engine:
                e_vg: EngineVoiceGroup
                MY_LOGGER.debug(f'VGroup: {e_vg.vg_name} #voices: {len(e_vg.e_voices)}')
                if len(e_vg.e_voices) > 1:
                    for ev in e_vg.e_voices:
                        MY_LOGGER.debug(f'ev: {ev}')
                v_choices: VoiceChoices
                v_choices = cls.create_voice_choices_from_vg(e_vg)
                qual: QualityType = e_vg.voice_quality

                count: int = len(v_choices)
                MY_LOGGER.debug(f'Adding VGChoice {e_vg.vg_name}')
                MY_LOGGER.debug(f'e_vg lang_tag: {e_vg.lang_tag} match: '
                                f'{e_vg.locale_match} quality: '
                                f'{e_vg.voice_quality_label}')
                vg_choice: VGChoice
                vg_choice = VGChoice.add(label=e_vg.vg_name,
                                         choice_idx=len(vg_choice_list),
                                         enabled=True,
                                         hint=None,
                                         e_vg=e_vg,
                                         v_choices=v_choices)
                vg_choice_list.append(vg_choice)
                #  MY_LOGGER.debug(f'vgChoice: {vg_choice}')
            vg_choices: VGChoices
            vg_choices = VGChoices.add(engine_key=engine_key,
                                       selected_vg_idx=-1,
                                       default_vg_idx=default_vg_idx,
                                       new_list=vg_choice_list)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'vg_choices: {vg_choices}')
            vg_choices.sort_by_sort_key()
            vg_idx: int = -1
            vg_choices.best_idx = 0  # 'Best' group is the first
            vg_choices.selected_vg_idx = 0
            vg_choices.default_vg_idx = 0
            for vg_choice in vg_choices:
                vg_choice: VGChoice
                vg_idx += 1
                vg_choice.choice_idx = vg_idx
                vg_choice.default_v_idx = 0
                vg_choice.best_v_idx = 0  # 'Best' Voice in group is the first
                if MY_LOGGER.isEnabledFor(DEBUG_V):
                    MY_LOGGER.debug_v(f'vg: {vg_choice.label} uid: '
                                      f'{vg_choice.e_vg.vg_uid}')
                vg_choice.v_choices.sort_by_sort_key()
                if MY_LOGGER.isEnabledFor(DEBUG_XV):
                    for v_choice in vg_choice.v_choices:
                        v_choice: VoiceChoice
                        MY_LOGGER.debug_xv(f'v_choice: {v_choice.label} e_voice_id: '
                                           f'{v_choice.e_voice.e_voice_id}')
                # After sorting, fix up any indexes
                # The best voice in a VG should already be the first one in the VG
                v_idx: int = 0
                for v_choice in vg_choice.v_choices:
                    v_choice.choice_idx = v_idx
                    v_idx += 1
            try:
                # Now take into account the current voice setting of each engine is
                current_e_voice: EngineVoice
                current_e_voice = EngineVoiceManager.get_e_voice(engine_key)
                # Best voice should be the first voice in the first VoiceGroup in
                # VoiceGroups
                vg_choices.best_vg_idx = 0
                best_vg: VGChoice = vg_choices[0]
                best_vg.best_v_idx = 0
                best_voice: VoiceChoice = best_vg.v_choices[0]
                best_vg.v_choices.best_idx = 0
                if current_e_voice is None:
                    current_e_voice = best_voice.e_voice
                current_vg_id: str = current_e_voice.engine_vg_id
                MY_LOGGER.debug(f'current_vg_id: {current_vg_id}')
                current_voice: VoiceChoice | None
                current_voice = ChoiceDict.voice_by_uid.get(current_e_voice.uid,None)
                if current_voice is None:
                    raise ValueError('Could not find voice for ev_uid: '
                                     f'{current_e_voice.e_voice_id}')
                current_vg: VGChoice = current_voice.vg_choice
                current_voice.select()
                vg_choices.selected_vg_idx = current_vg.choice_idx
                current_vg.select_v_idx = current_voice.choice_idx

                # Sanity Check
                for vg_choice in vg_choices:
                    vg_choice: VGChoice
                    if not isinstance(vg_choice, VGChoice):
                        raise TypeError(f'Expected VGChoice, got {type(vg_choice)}')
                    if MY_LOGGER.isEnabledFor(DEBUG_XV):
                        MY_LOGGER.debug_xv(f'choice-type: {type(vg_choice)}')
                        if vg_choice.has_single_voice:
                            MY_LOGGER.debug_xv(f'simple voice: {vg_choice}')

                        MY_LOGGER.debug_xv(f'vg_choice.engine_vg_id: '
                                           f'{vg_choice.engine_vg_id} '
                                           f'current_vg_id: {current_vg_id}')
            except Exception as e:
                MY_LOGGER.exception('')
            #  cls.dump_vg_info(result.vg_choices)
            ChoiceDict.vg_choices_for_engine_id[engine_key] = vg_choices
            return vg_choices
        except Exception:
            MY_LOGGER.exception('')
        vg_choices: VGChoices
        vg_choices = VGChoices.add(engine_key=engine_key,
                                   selected_vg_idx=-1,
                                   default_vg_idx=-1,
                                   new_list=[])
        return vg_choices

    @classmethod
    def dump_vg_info(cls, values: VGChoices) -> None:
        #
        # vg_choices, selected & default indices
        MY_LOGGER.debug(f'Dumping VGChoices')
        values.dbg_print2()

    @classmethod
    def create_voice_choices_from_vg(cls,
                                     e_vg: EngineVoiceGroup) -> VoiceChoices:
        voice_choices: VoiceChoices = VoiceChoices()
        idx: int = 0
        for e_voice in e_vg.e_voices.values():
            e_voice: EngineVoice
            voice_choice: VoiceChoice | None = None
            voice_choice = ChoiceDict.voice_by_uid.get(e_voice.uid, None)
            if voice_choice is None:
                voice_choice = VoiceChoice.add(e_voice=e_voice,
                                               e_vg=e_vg,
                                               label=e_voice.voice_label,
                                               choice_idx=idx,
                                               enabled=True,
                                               hint=None)
                MY_LOGGER.debug(f'voice_choice: {voice_choice.label} e_voice:'
                                f'{voice_choice.e_voice} ')
            elif MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'v_choice already exists: {voice_choice.label}')
            idx += 1
            voice_choices.append(voice_choice)
        return voice_choices
