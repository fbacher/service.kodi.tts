# coding=utf-8
from __future__ import annotations

import logging
from collections import UserList
from typing import Any, Dict, ForwardRef, List

from backends.settings.engine_lang import EngineLang
from backends.settings.engine_voice import EngineVoice
from backends.settings.engine_voice_group import EngineVoiceGroup
from backends.settings.engine_voice_manager import EngineVoiceManager
from backends.settings.lang_utils import LangUtils
from backends.settings.service_types import EngineType, QualityType, ServiceID
from common.logger import *

MY_LOGGER = BasicLogger.get_logger(__name__)


class Choices(UserList):
    """
    How Selection is handled for Voices and Voice Groups.

    Generally, the object is the target of the selection/deselction is in charge.

    Currently, only Piper has the concept of multiple speakers for a voice
    (TODO: Check terminology). Here, the terminology VoceGroup and Voices are used.
    A VoiceGroup is a collection of Voices which share a data file which describes
    the basic voice. Each Voice adds some tweaks which allow the speakers to sound
    different from one another. One advantage to this is to make it easier (cheaper,
    resource wise) to support multiple speakers, since the cost of loading and
    initializing the speech engine is greatly reduced whenever a different speaker
    (Voice) is used. The first few use cases will focus on the use of Voice Groups
    and Voices.

    Use Cases
    1- User is viewing the first Voices dialog for Piper. Here you see mostly
       Voice-Groups but also some Voice-Groups with a single Voice, so they show
       up as Voices. The user wants the last selected or default VoiceGroup to be
       selected when the dialog appears.
    2- When a user sees a VoiceGroup they want to see the selected/default
       voice information included with the VoiceGroup.
    3- When a user selects a Voice-Group, the user wants a) the selected Voice-Group
       to become the new selected Voice-Group.
    4- When a user double-clicks, presses OK button, etc., the user expects that
       when more than one voice is in the group, that a second dialog only showing
       the voices in the selected group to display. The user expects the default
       or previously selected voice to be selected and focused.
    5- When a user selects another voice, the user expects that 1) the previous
       selection is forgotton and replaced with the newly selected voice.

    """

    initialized: bool = False

    def __init__(self, new_list: UserList | List | None = None) -> None:
        if new_list is None:
            new_list = []
        super().__init__(new_list)
        # Index to the default choice. Used when all else fails. Typically
        # zero.
        self._default_idx: int = -1
        # Index of the currently selected choice. Initially set to the value
        # in settings.xml
        self._selected_idx: int = -1
        # Index of the 'best' choice available, typically based on a trivial
        # heuristic or personal bias. Ex: for a voice, a lot of weight is given
        # to how close the locale of the voice matches Kodi's locale.
        self._best_idx: int = -1

    @property
    def default_idx(self) -> int:
        """
           Index to the default choice. Used when all else fails. Typically
           zero.
        """
        return self._default_idx

    @default_idx.setter
    def default_idx(self, idx: int) -> None:
        """
           Index to the default choice. Used when all else fails. Typically
           zero.
        """
        if idx >= len(self):
            if len(self) == 0:
                idx = -1
            else:
                raise ValueError(f'default_idx: {idx} must be less than length:'
                                 f' {len(self)}')
        self._default_idx = idx

    @property
    def selected_idx(self) -> int:
        """
            Index of the currently selected choice. Initially set to the value
            in settings.xml
        """
        return self._selected_idx

    @property
    def best_idx(self) -> int:
        """
          Index of the 'best' choice available, typically based on a trivial
          heuristic or personal bias. Ex: for a voice, a lot of weight is given
          to how close the locale of the voice matches Kodi's locale.
        """
        return self._best_idx

    @best_idx.setter
    def best_idx(self, idx: int) -> None:
        """
          Index of the 'best' choice available, typically based on a trivial
          heuristic or personal bias. Ex: for a voice, a lot of weight is given
          to how close the locale of the voice matches Kodi's locale.
        """
        self._best_idx = idx

    def sort_by_engine_label(self) -> None:
        self.sort(key=lambda entry: entry.label)

    def sort_by_sort_key(self) -> None:
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            for choice in self:
                MY_LOGGER.debug_xv(f'sort_key: {choice.sort_key}')
        self.sort(key=lambda entry: entry.sort_key)

    def dbg_print(self) -> str:
        result: str = ''
        for choice in self.data:
            choice: Choice
            result = f'{result}\n {choice}'
        return result

    def __str__(self) -> str:
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            for choice in self.data:
                choice: Choice
                result = f'{result}\n {choice}'
        return result


class EngineChoices(Choices):
    """
    TODO: Change to make Choices Generic
    """

    def __init__(self,
                 new_list: UserList['EngineChoice'] | List['EngineChoice'] | None = None) -> None:
        if new_list is None:
            new_list: List['EngineChoice'] = []

        if MY_LOGGER.isEnabledFor(DEBUG):
            for choice in new_list:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    if not isinstance(choice, EngineChoice):
                        MY_LOGGER.debug(f'Expected EngineChoice not: {type(choice)}')
        super().__init__(new_list)

    @property
    def best_engine(self) -> 'EngineChoice':
        best_idx = self.best_idx
        engine_choice: EngineChoice = self[best_idx]
        return engine_choice

    @property
    def default_engine(self) -> 'EngineChoice':
        default_idx = self.default_idx
        engine_choice: EngineChoice = self[default_idx]
        return engine_choice

    @property
    def selected_engine(self) -> 'EngineChoice':
        idx = self.selected_idx
        engine_choice: EngineChoice = self[idx]
        return engine_choice


class VGChoices(Choices):
    """
    TODO: Change to make Choices Generic
    """

    @classmethod
    def get_vg_choices(cls, engine_key: ServiceID) -> 'VGChoices':
        """
        Gets all VGChoices for the given engine_key.

        :param engine_key: Engine which this list of VGroups belong
        """
        vg_choices: VGChoices | None
        vg_choices = ChoiceDict.vg_choices_for_engine_id.get(engine_key)
        if vg_choices is None:
            raise ValueError(f'No VGChoices for {engine_key}')

        return vg_choices

    @classmethod
    def add(cls, engine_key: ServiceID,
            selected_vg_idx: int = -1,
            default_vg_idx: int = -1,
            new_list: UserList['VGChoice'] | List[
                'VGChoice'] | None = None) -> 'VGChoices':
        vg_choices: VGChoices | None
        vg_choices = ChoiceDict.vg_choices_for_engine_id.get(engine_key)
        if vg_choices is None:
            vg_choices = VGChoices(engine_key, selected_vg_idx, default_vg_idx, new_list)
            vg_choices: VGChoices
        return vg_choices

    def __init__(self, engine_key: ServiceID,
                 selected_vg_idx: int = -1,
                 default_vg_idx: int = -1,
                 new_list: UserList['VGChoice'] | List['VGChoice'] | None = None) -> None:
        if new_list is None or len(new_list) == 0:
            raise ValueError('Empty list of voices')
        if MY_LOGGER.isEnabledFor(DEBUG):
            for item in new_list:
                if not isinstance(item, VGChoice):
                    MY_LOGGER.debug(f'Expected VGChoice not: {type(item)}')
        super().__init__(new_list)
        self._best_vg_idx: int = -1
        self._selected_vg_idx: int = -1
        self._engine_key: ServiceID = engine_key
        self.selected_vg_idx = selected_vg_idx
        self.default_vg_idx: int = default_vg_idx
        ChoiceDict.vg_choices_for_engine_id[engine_key] = self
        if not isinstance(self, VGChoices):
            MY_LOGGER.debug(f'type should be VGChoices: {type(self)}')

    @property
    def choices(self) -> 'VGChoices':
        return ChoiceDict.vg_choices_for_engine_id.get(self._engine_key)

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    @property
    def best_vg_idx(self) -> int:
        return self._best_vg_idx

    @best_vg_idx.setter
    def best_vg_idx(self, value: int) -> None:
        self._best_vg_idx = value

    @property
    def selected_vg_idx(self) -> int:
        return self._selected_vg_idx

    @selected_vg_idx.setter
    def selected_vg_idx(self, value: int) -> None:
        limit: int = 0
        vg_choices = self.choices
        if vg_choices is not None:
            limit = len(vg_choices)
        if value >= limit:
            raise ValueError(f'trying to set selected_vg_idx out of range '
                             f'{value} limit: {limit - 1}')
        self._selected_vg_idx = value

    @property
    def selected_vg_obj(self) -> 'VGChoice':
        return self.choices[self.selected_vg_idx]

    @property
    def selected_v_obj(self) -> 'VoiceChoice':
        return self.selected_vg_obj.selected_v_obj

    @property
    def default_vg_idx(self) -> int:
        return self._default_vg_idx

    @default_vg_idx.setter
    def default_vg_idx(self, value: int) -> None:
        limit: int = 0
        vg_choices = self.choices
        if vg_choices is not None:
            limit = len(vg_choices)
        if value >= limit:
            raise ValueError(f'trying to set default_vg_idx out of range '
                             f'{value} limit: {limit - 1}')
        self._default_vg_idx = value

    def select_vg(self, voice_group: 'VGChoice') -> None:
        """
        Selects the given VoiceGroup for the current engine.

        Note that voice_group.select_vg is also called

        :param voice_group: VoiceGroup to select
        """
        self.selected_vg_idx = voice_group.choice_idx
        MY_LOGGER.debug(f'vg.select_vg: {voice_group} idx: {voice_group.choice_idx}')
        voice_group.select_vg()

    def _select_vg(self, voice_group: 'VGChoice') -> None:
        """
        Similar to select_vg, except that the voice_group.select_vg method is
        not called, avoiding recursion if voice_group.select_vg is called.

        :param voice_group: VoiceGroup to select
        """
        MY_LOGGER.debug(f'vg._select_vg: {voice_group} idx: {voice_group.choice_idx}')

        self.selected_vg_idx = voice_group.choice_idx

    def dbg_print2(self) -> None:
        for choice in self:
            choice: VGChoice
            choice.dbg_print2()


class VoiceChoices(Choices):
    """
    TODO: Change to make Choices Generic
    """

    def __init__(self, new_list: UserList['VoiceChoice'] | List | None = None) -> None:
        if new_list is None:
            new_list = []
        if MY_LOGGER.isEnabledFor(DEBUG):
            for item in new_list:
                if not isinstance(item, VoiceChoice):
                    MY_LOGGER.debug(f'Expected VoiceChoice not: {type(item)}')
        super().__init__(new_list)


class Choice:
    """
    Encapsulates information for making a settings choice.

    Typically, contains display_value, id and choice_index. May contain more
    items, as needed. By containing the choice variants here, the users of this
    class don't have to change whenever a new variant is is_required.
    """

    def __init__(self, label: str, value: str, choice_idx: int,
                 sort_key: str = None, enabled: bool = True,
                 engine_key: ServiceID = None,
                 match_distance: int = 1000, hint: str = None) -> None:
        """

        """
        if sort_key is None:
            sort_key = label
        self._label: str = label
        self._hint: str = hint
        self._value: str = value
        self._choice_idx: int = -1
        self.choice_idx = choice_idx
        self._engine_key: ServiceID = engine_key
        self._sort_key: str = sort_key
        self._enabled: bool = enabled
        self._match_distance: int = match_distance

    @property
    def label(self) -> str:
        MY_LOGGER.debug(f'Choice label: {self._label}')
        return f'{self._label}'

    @property
    def hint(self) -> str:
        return self._hint

    @hint.setter
    def hint(self, value: str) -> None:
        self._hint = value

    @property
    def value(self) -> str:
        return self._value

    def _set_value(self, value: str):
        self._value = value

    @property
    def choice_idx(self) -> int:
        return self._choice_idx

    @choice_idx.setter
    def choice_idx(self, value: int) -> None:
        self._choice_idx = value

    @property
    def engine_key(self) -> ServiceID:
        return self._engine_key

    def set_engine_key(self, engine_key: ServiceID) -> None:
        self._engine_key = engine_key

    @property
    def sort_key(self) -> str:
        return self._sort_key

    def _set_sort_key(self, sort_key: str) -> None:
        self._sort_key = sort_key
        MY_LOGGER.debug(f'sort_key: {sort_key}')

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def match_distance(self) -> int:
        return self._match_distance

    def set_match_distance(self, match_distance: int) -> None:
        self._match_distance = match_distance

    def __str__(self) -> str:
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            result = f'label: {self.label}'
        elif MY_LOGGER.isEnabledFor(DEBUG_XV):
            result = (f'label: {self.label}\n'
                      f'hint: {self.hint}\n'
                      f'value: {self.value}\n'
                      f'choice_index: {self.choice_idx}\n'
                      f'engine_key: {self.engine_key}\n'
                      f'sort_key: {self.sort_key}\n'
                      f'enabled: {self.enabled}\n'
                      f'match_distance: {self.match_distance}\n')
        return result

    def __rpr__(self) -> str:
        return self.__str__()


class EngineChoice(Choice):
    """
    Encapsulates information for making an Engine choice.
    """

    def __init__(self, label: str, value: EngineType, choice_index: int = -1,
                 sort_key: str = None, enabled: bool = True,
                 engine_key: ServiceID = None,
                 match_distance: int = 1000, hint: str = None,
                 lang: EngineLang = None,
                 voice: EngineVoice | None = None,
                 new_voice: EngineVoice | None = None) -> None:
        """
        :param label: User-friendly, translated label
        :param hint: User-friendly, translated hint
        :param value: value used in settings, etc.
        :param choice_index: When from a list of choices, this is its place in list.
        :param sort_key:  Key to use when sorting list
        :param enabled:   Some settings may not be usable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        :param engine_key: Identifies which engine this setting is associated with
        :param lang: language information
        :param voice: default voice to use when this engine is selected
        :param new_voice: Voice to use when this engine is selected
        :param match_distance: for language related settings. Represents how close
                               this choice is to the desired language. For example,
                               a voice for en-GB is not as close to en-US as an
                               en-US one, but close enough to use. Comes from
                               langcodes.
        """
        super().__init__(label=label,
                         value=value,
                         choice_idx=choice_index,
                         sort_key=sort_key,
                         enabled=enabled,
                         engine_key=engine_key,
                         hint=hint,
                         match_distance=match_distance)
        if MY_LOGGER.isEnabledFor(DEBUG):
            if lang is not None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    if not isinstance(lang, EngineLang):
                        MY_LOGGER.debug(f'Expected EngineLang not {type(lang)}')
            if voice is not None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    if not isinstance(voice, EngineVoice):
                        MY_LOGGER.debug(f'Expected EngineVoice not {type(voice)}')

            if new_voice is not None:
                if MY_LOGGER.isEnabledFor(DEBUG):
                    if not isinstance(new_voice, EngineVoice):
                        MY_LOGGER.debug(f'Expected EngineVoice not {type(new_voice)}')
        lang: EngineLang
        voice: EngineVoice
        self.lang: EngineLang = lang
        self.voice: EngineVoice = voice
        if new_voice is not None:
            self.new_voice: EngineVoice = new_voice
        else:
            self.new_voice: EngineVoice = voice

    @property
    def label(self) -> str:
        return f'{self._label}'

    @classmethod
    def dbg_print(cls, choices: EngineChoices) -> None:
        for choice in choices:
            choice: EngineChoice
            MY_LOGGER.debug(f'Choice {choice}')
            MY_LOGGER.debug('')

    def __str__(self) -> str:
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            result = (f'EngineChoice: {self.label} \n'
                      f'lang: {self.lang}\n'
                      f'voice: {self.voice}\n'
                      f'new_voice: {self.new_voice}\n')
        elif MY_LOGGER.isEnabledFor(DEBUG_XV):
            result = (f'EngineChoice: {super().__str__()}\n'
                      f'lang: {self.lang}\n'
                      f'voice: {self.voice}\n'
                      f'new_voice: {self.new_voice}\n')
        return result

    def __rpr__(self) -> str:
        return self.__str__()


class VGChoice(Choice):
    """
    Encapsulates information for making a Voice choice.

    EngineVGs are motivated by TTS engine Piper, which has the concept
    of groups of voices (Piper refers to the group as a Voice and the
    members as Speakers). In Kodi TTS a voice always belongs to a VGChoice,
    resulting in mostly EngineVGs with one Voice.

    To choose a voice, the user (or auto-configuration code) first gets the
    information on the EngineVGs (quality, locale, engine, etc.). In the
    UI the user will see the EngineVGs, with one per line in a scrollable
    dialog.

    A VGChoice with more than one voice in it will indicate that it is a
    group. It will give its name, a voice quality of the group and other basic
    info.

    A VGChoice with just one voice will have slighly different information
    presented. It will give the voice name and its target locale; the quality,
    gender, if any, among other things.

    When a user focuses on a Voice, TTS will switch to use it to announce text.

    When a user focuses on a VGChoice, TTS will switch to use its default
    voice to announce text.

    When a user selects a VGChoice, a new dialog will appear and the voice
    members of the group will be displayed, with the default voice as the first
    in the list, with focus and with TTS using that voice. As the user navigates
    to other voices in the group, they will become TTS's voice.
    """

    @classmethod
    def add(cls,
            e_vg: EngineVoiceGroup,
            label: str,
            choice_idx: int = -1,
            default_idx: int = -1,
            enabled: bool = True,
            hint: str = None,
            v_choices: 'VoiceChoices' = VoiceChoices()) -> 'VGChoice':
        """
        :param e_vg: EngineVoiceGroup (required)
        :param label: User-friendly, translated label (required)
        :param choice_idx: When from a list of choices, this is its place in list.
        :param default_idx: 0 before sorting of voices. Recalculated after sorting
        :param hint: User-friendly, translated hint
        :param enabled:   Some settings may not be useable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        :param v_choices: VoiceChoices to add to this VGChoice
        """
        vg_choice: VGChoice
        vg_choice = ChoiceDict.vg_by_uid.get(e_vg.uid)
        if MY_LOGGER.isEnabledFor(DEBUG):
            if not isinstance(e_vg, EngineVoiceGroup):
                MY_LOGGER.debug(f'Expected e_vg EngineVoiceGroup not {type(e_vg)}')
            if not isinstance(v_choices, VoiceChoices):
                MY_LOGGER.debug(f'Expected v_choices VoiceChoices not {type(v_choices)}')
        if vg_choice is None:
            vg_choice = VGChoice(e_vg, label,
                                 default_idx,
                                 choice_idx,
                                 enabled,
                                 hint,
                                 v_choices)

            ChoiceDict.vg_by_uid[e_vg.uid] = vg_choice
        return vg_choice

    def __init__(self,
                 e_vg: EngineVoiceGroup,
                 label: str,
                 choice_idx: int = -1,
                 default_idx: int = -1,
                 enabled: bool = True,
                 hint: str = None,
                 v_choices: 'VoiceChoices' = VoiceChoices()) -> None:
        """
        :param e_vg: EngineVoiceGroup (required)
        :param label: User-friendly, translated label (required)
        :param choice_idx: When from a list of choices, this is its place in list.
        :param default_idx: 0 before sorting of voices. Recalculated after sorting
        :param hint: User-friendly, translated hint
        :param enabled:   Some settings may not be useable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        :param v_choices: VoiceChoices to add to this VGChoice
        """
        engine_key = e_vg.engine_key
        value = e_vg.engine_vg_id
        match_distance = e_vg.locale_match
        kodi_ietf_tag = LangUtils.kodi_locale
        e_lang_uid: str = EngineLang.get_uid(e_vg.engine_key, kodi_ietf_tag)
        e_lang = EngineVoiceManager.get_eng_lang_by_uid(e_lang_uid)
        e_lang: EngineLang

        # Improve heuristic. These expand to two fixed-width numbers.
        # Less is better
        qual: str = f'{e_vg.voice_quality.ordinal:0d}'
        match: str = f'{match_distance:04d}'
        sort_key = f'{qual}:{match}:{label}'
        #  MY_LOGGER.debug(f'sort_key: {sort_key}')

        super().__init__(label=label,
                         value=value,
                         engine_key=engine_key,
                         choice_idx=choice_idx,
                         sort_key=sort_key,
                         enabled=enabled,
                         match_distance=match_distance,
                         hint=hint)

        self.e_lang: EngineLang = e_lang
        self._selected: bool = False
        # Track which voice is selected, default is
        self._best_v_idx: int = -1
        self._selected_v_idx: int = -1
        self._selected_v_obj: 'VoiceChoice | None' = None
        self._default_v_idx: int = -1
        self._e_vg: EngineVoiceGroup = e_vg
        self.v_choices: VoiceChoices = v_choices
        self._v_for_uid: Dict[str, VoiceChoice] = {}
        for v_choice in self.v_choices:
            v_choice: VoiceChoice
            v_choice.vg_choice = self
            self._v_for_uid[v_choice.e_voice.uid] = v_choice

        self._uid: str = e_vg.uid

    @property
    def best_v_idx(self) -> int:
        return self._best_v_idx

    @best_v_idx.setter
    def best_v_idx(self, idx: int) -> None:
        self._best_v_idx = idx

    @property
    def default_v_idx(self) -> int:
        return self._default_v_idx

    @default_v_idx.setter
    def default_v_idx(self, idx: int = 0) -> None:
        if idx >= len(self.v_choices):
            raise ValueError(f'default_voice_idx is out of range: {idx} max: '
                             f'{len(self.v_choices) - 1}')
        self._default_v_idx = idx

    def select_vg(self) -> None:
        """
        Mark this VGChoice as selected, unmark every other VGChoice for the same
        engine.
        """
        if not self._selected:
            self._selected = True

        # Do whatever is needed after a selection
        # Mark containing VoiceGroup so that when voiceGroup is displayed,
        # correct voice is displayed.

    def select_voice(self, v_idx: int = -1) -> int:
        """
        Select a Voice from this group. If voice_id is specified, then that
        voice is selected, otherwise, if self.selected_v_idx is not -1, then
        that voice is selected, otherwise, the default voice is selected.

        :param v_idx: index of VoiceChoices to select.
        :return: Voice index that was actually selected
        """
        if not self._selected:
            self._selected = True

        voice_to_select_idx: int = 0
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'vg: {self._label} voice_id: {v_idx} selected_v_idx:'
                               f' {self._selected_v_idx} '
                               f'default_voice_idx: {self._default_v_idx}\n')
        if v_idx != -1:
            voice_to_select_idx = v_idx
        elif self._selected_v_idx != -1:
            voice_to_select_idx = self._selected_v_idx
        elif self.default_v_idx != -1:
            voice_to_select_idx = self.default_v_idx
        MY_LOGGER.debug(f'selected_v_idx: {voice_to_select_idx}')
        self.selected_v_idx = voice_to_select_idx
        default_voice_choice: VoiceChoice = self.v_choices[voice_to_select_idx]
        default_voice_choice.select()
        return voice_to_select_idx

    @property
    def selected_v_obj(self) -> 'VoiceChoice':
        return self.v_choices[self._selected_v_idx]

    # @selected_v_obj.setter
    # def selected_v_obj(self, v_obj: 'VoiceChoice') -> None:
    #     self._selected_v_obj = v_obj

    def v_for_uid(self, uid: str) -> 'VoiceChoice | None':
        return self._v_for_uid.get(uid)

    def dbg_print2(self) -> None:
        e_vg: EngineVoiceGroup = self.e_vg
        result: str = (f'VGC: {self.e_lang} '
                       f'dist: {self.match_distance} '
                       f'qual: {e_vg.voice_quality_label} '
                       f'lbl: {self.label} '
                       f'mtch: {self.match_distance} '
                       f'srt: {self.sort_key} '
                       f'enbl: {self.enabled}')
        MY_LOGGER.debug(result)

    @property
    def e_vg(self) -> EngineVoiceGroup:
        return self._e_vg

    @property
    def engine_vg_id(self) -> str:
        return self._e_vg.engine_vg_id

    @property
    def has_single_voice(self) -> bool:
        return self.e_vg.has_single_voice

    @property
    def selected_v_idx(self) -> int:
        #  MY_LOGGER.debug(f'selected_v_idx: {self._selected_v_idx}'
        #                  f' group: {self._label}')
        if self._selected_v_idx < 0:
            self._selected_v_idx: int = self.select_voice(v_idx=self._selected_v_idx)
        return self._selected_v_idx

    @selected_v_idx.setter
    def selected_v_idx(self, value: int) -> None:
        """
        Sets the selected voice index. Also sets the selected_v_obj
        Note the initial selected voice is the currently configured voice

        """
        MY_LOGGER.debug(f'VGChoice.Setting selected_v_idx to {value} VGroup:'
                        f' {self._label}')
        if value >= len(self.v_choices):
            raise ValueError(f'Setting selected_v_idx out of RANGE. \n'
                             f'Value given: {value} # voices: {len(self.v_choices)}')
        self._selected_v_idx = value
        MY_LOGGER.debug(f'Just set _selected_v_idx')

    def set_selected_ev_id(self, e_voice_id: str) -> int:
        """
        Selects a particular voice within this group of voices.

        :param e_voice_id: Identifies the voice to select
        :return: VGChoice index of voice identified by e_voice_id
        """
        v_choice: VoiceChoice | None = self.v_for_uid(e_voice_id)
        if v_choice is None:
            raise ValueError(f'No VoiceChoice for e_voice_id: {e_voice_id} '
                             f'vg: {self.label}')
        MY_LOGGER.debug(f'set_selected_ev_id: {v_choice.choice_idx}')
        self.selected_v_idx = v_choice.choice_idx
        MY_LOGGER.debug(f'Selected voice: {self.selected_v_idx} group: {self.label}'
                        f' voice_id:{e_voice_id} ev_uid: {v_choice.e_voice.uid}')
        return v_choice.choice_idx

    @property
    def label(self) -> str:
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'selected_v_idx: {self._selected_v_idx}'
                               f' choice_idx {self.choice_idx}')
        self.select_voice()
        selected_voice: VoiceChoice = self.v_choices[self.selected_v_idx]
        #  return selected_voice._label
        new_label: str = self._e_vg.full_vg_label(selected_voice.e_voice.e_voice_id)
        return new_label

    @label.setter
    def label(self, label: str) -> None:
        """
        Changes the label of the choice. Used when VGChoice's
        """
        MY_LOGGER.debug(f'Setting label to {label}')
        self._label = label

    @classmethod
    def dbg_print(cls, choices: VGChoices) -> None:
        for choice in choices:
            choice: Choice
            MY_LOGGER.debug(f'Choice {choice}')
            MY_LOGGER.debug('')

    @property
    def uid(self) -> str:
        """
            Unique id for the voice group
        """
        if self._uid is None:
            self._uid = self._e_vg.uid
        return self._uid

    def __str__(self) -> str:
        result: str = ''
        if not MY_LOGGER.isEnabledFor(DEBUG):
            return result

        if MY_LOGGER.isEnabledFor(DEBUG):
            result = f'VGChoice: {self.label}'
        elif MY_LOGGER.isEnabledFor(DEBUG_XV):
            result = f'VGChoice: {super().__str__()}'
        result = (f'{result}\n'
                  f'e_lang: {self.e_lang}\n'
                  f'selected_v_idx: {self.selected_v_idx}\n'
                  f'e_vg: {self.e_vg}\n')
        return result

    def __rpr__(self) -> str:
        return self.__str__()


class VoiceChoice(Choice):
    """
    Encapsulates information for making a Voice choice.
    """

    @classmethod
    def add(cls, e_voice: EngineVoice,
            e_vg: EngineVoiceGroup,
            label: str | None = None,
            choice_idx: int = -1,
            enabled: bool = True,
            hint: str = None) -> 'VoiceChoice':
        """
        Convenience method that creates or reuses an existing voice to its voice group.

        :param e_voice: EngineVoice
        :param e_vg: Voice Group that this voice is a member of
        :param label: User-friendly, translated label
        :param choice_idx: Index into parent VGroup's for this voice
        :param hint: User-friendly, translated hint
        :param enabled:   Some settings may not be usable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            if not isinstance(e_voice, EngineVoice):
                MY_LOGGER.debug(f'Expected e_voice EngineVoice not {type(e_voice)}')
            if not isinstance(e_vg, EngineVoiceGroup):
                MY_LOGGER.debug(f'Expected v_choices EngineVoiceGroup not {type(e_vg)}')

        voice_choice = ChoiceDict.voice_by_uid.get(e_voice.uid, None)
        if voice_choice is not None:
            MY_LOGGER.debug(f'v_choice already exists: {voice_choice.label}')
        else:
            voice_choice = VoiceChoice(e_voice, e_vg, label, choice_idx=choice_idx,
                                       enabled=enabled, hint=hint)
            ChoiceDict.voice_by_uid[e_voice.uid] = voice_choice
        return voice_choice

    def __init__(self, e_voice: EngineVoice,
                 e_vg: EngineVoiceGroup,
                 label: str | None = None,
                 choice_idx: int = -1,
                 enabled: bool = True,
                 hint: str = None) -> None:
        """
        :param e_voice: EngineVoice
        :param e_vg: Voice Group that this voice is a member of
        :param label: User-friendly, translated label
        :param choice_idx: Index into parent VGroup's for this voice
        :param hint: User-friendly, translated hint
        :param enabled:   Some settings may not be usable depending on other settings
                          We want to include disabled choices to show a consistent list,
                          but marked in UI as disabled
        # :param engine_key: Identifies which engine this setting is associated with
        # :param match_distance: for language related settings. Represents how close
        #                        this choice is to the desired language. For example,
        #                        a voice for en-GB is not as close to en-US as a
        #                        en-US one, but close enough to use. Comes from
        #                        langcodes.
        """
        voice_choice = ChoiceDict.voice_by_uid.get(e_voice.uid, None)
        if voice_choice is not None:
            raise ValueError(f'v_choice already exists: {voice_choice.label}')

        if label is None:
            label = e_voice.voice_label
        engine_key = e_voice.engine_key
        value = engine_key.service_id
        kodi_ietf_tag = LangUtils.kodi_locale
        e_lang_uid: str = EngineLang.get_uid(e_vg.engine_key, kodi_ietf_tag)
        e_lang = EngineVoiceManager.get_eng_lang_by_uid(e_lang_uid)

        match_distance = e_vg.locale_match
        v_quality: QualityType = e_vg.voice_quality
        # Improve heuristic. These expand to two fixed-width numbers.
        # Less is better
        qual: str = f'{v_quality.ordinal:0d}'
        match: str = f'{match_distance:04d}'
        sort_key = f'{qual}:{match}:{label}'
        #  MY_LOGGER.debug(f'sort_key: {sort_key}')

        super().__init__(label=label,
                         value=value,
                         sort_key=sort_key,
                         enabled=enabled,
                         choice_idx=choice_idx,
                         engine_key=engine_key,
                         hint=hint,
                         match_distance=match_distance)

        self._vg_choice: VGChoice = None
        self._e_lang: EngineLang = e_lang
        self._e_vg: EngineVoiceGroup = e_vg
        self._e_voice: EngineVoice = e_voice
        self._enabled: bool = enabled

    @property
    def e_voice(self) -> EngineVoice:
        return self._e_voice

    @property
    def label(self) -> str:
        new_label: str = self._e_voice.full_voice_label()
        if MY_LOGGER.isEnabledFor(DEBUG_XV):
            MY_LOGGER.debug_xv(f'VoiceChoice label: {new_label}')
        return new_label

    @label.setter
    def label(self, new_label: str) -> None:
        MY_LOGGER.debug(f'Setting label: {new_label}')
        self._label = new_label

    @property
    def e_vg(self) -> EngineVoiceGroup:
        return self._e_vg

    def select(self) -> None:
        """
        Selection of voices is tracked by the parent VoiceGroup.
        """
        MY_LOGGER.debug(f'VoiceChoice.select: {self.choice_idx}')
        self.vg_choice.selected_v_idx = self.choice_idx

    @property
    def vg_choice(self) -> VGChoice:
        """
        References parent VoiceGroup
        """
        return self._vg_choice

    @vg_choice.setter
    def vg_choice(self, new_vg_choice: VGChoice) -> None:
        if self._vg_choice is not None:
            raise ValueError(f'vg_choice already exists: {self._vg_choice.label}')

        if MY_LOGGER.isEnabledFor(DEBUG):
            if not isinstance(new_vg_choice, VGChoice):
                MY_LOGGER.debug(f'Expected e_voice VGChoice not {type(new_vg_choice)}')
        self._vg_choice = new_vg_choice

    @property
    def voice_label(self) -> str:
        """
        Gets the label for this voice

        :return: Only the Voice's label (does not include Voice Group)
        """
        return f'VoiceChoice {self.e_voice.voice_label}'

    @property
    def full_voice_label(self) -> str:
        """
        Inclues Voice Group's label, if any.

        :return: The Voice_Group's label along with the Voice label
        """
        return f'VoiceChoice: {self._e_voice.full_voice_label()}'

    @classmethod
    def dbg_print(cls, choices: EngineChoices) -> None:
        for choice in choices:
            choice: Choice
            MY_LOGGER.debug(f'Choice {choice}')
            MY_LOGGER.debug('')

    def dbg_print2(self) -> None:
        result: str = (f'VGC: {self.e_voice.lang} '
                       f'dist: {self.match_distance} '
                       f'qual: {self.e_voice.voice_quality_label} '
                       f'lbl: {self.label} '
                       f'mtch: {self.match_distance} '
                       f'srt: {self.sort_key} '
                       f'enbl: {self.enabled}')
        MY_LOGGER.debug(result)

    def __eq__(self, other):
        """
        Allow for equality checks. DOES NOT handle hash comparisions (maps)
        :param other:
        :return:
        """
        if isinstance(other, VoiceChoice):
            other: VoiceChoice
            return self.e_voice == other.e_voice
        return ValueError(f'Both operands must be VoiceChoice objects. Second is'
                          f' {type(other)}')

    def __str__(self) -> str:
        if not MY_LOGGER.isEnabledFor(DEBUG):
            return ''
        result: str = ''
        if MY_LOGGER.isEnabledFor(DEBUG):
            result = f'VoiceChoice: {self.label}'
        elif MY_LOGGER.isEnabledFor(DEBUG_XV):
            result = f'VoiceChoice: {super().__str__()}'
        result = (f'{result}\n'
                  f'voice: {self._e_voice}\n'
                  f'sort_key: {self.sort_key}\n'
                  f'enabled: {self.enabled}\n'
                  f'match_distance: {self.match_distance}\n')
        return result

    def __rpr__(self) -> str:
        return self.__str__()


class ChoiceDict:
    # Engine's ServiceID gives Dict[vg_id] of all of its VoiceGroups

    #  TODO: Never populated

    e_choices_for_engine_id: EngineChoices = []

    vg_choices_for_engine_id: Dict[ServiceID, VGChoices] = {}

    # Get VoiceGroups by engine, locale
    # vgs_by_engine_locale: Dict[ServiceID, Dict[str, VGChoices]] = {}

    # voice_group_uid (see get_uid()) gives its voice_group
    vg_by_uid: Dict[str, VGChoice] = {}

    # The second dict's key is voice_id
    voice_choice_for_voice_id: Dict[ServiceID, Dict[str, VoiceChoice]] = {}

    # voice_uid (see get_uid()) gives a voice
    voice_by_uid: Dict[str, VoiceChoice] = {}
