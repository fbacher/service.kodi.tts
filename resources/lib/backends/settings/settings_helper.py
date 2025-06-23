# coding=utf-8
from __future__ import annotations

from backends.settings.service_types import (ALL_ENGINES, ALL_PLAYERS, EngineType,
                                             PlayerType, ServiceID)

try:
    from enum import StrEnum
except ImportError:
    from common.strenum import StrEnum
from typing import Dict, ForwardRef, List, Tuple

import xbmc
import langcodes

from backends.backend_info import BackendInfo
from backends.i_tts_backend_base import ITTSBackendBase
from backends.settings.i_validators import AllowedValue, IStringValidator
from backends.settings.language_info import LanguageInfo
from backends.settings.service_types import ServiceType
from backends.settings.setting_properties import SettingProp
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import StringValidator
from common.debug import Debug
from common.exceptions import LogicError
from common.logger import *
from common.message_ids import MessageId
from common.setting_constants import GenderSettingsMap, PlayerMode
from common.settings import Settings
from windowNavigation.choice import Choice

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
    initialized: bool = False
    engine_id: str = None
    engine_instance: ITTSBackendBase | None = None
    allowed_player_modes: Dict[str, List[AllowedValue]] = {}

    @classmethod
    def init_class(cls) -> None:
        if not cls.initialized:
            #  cls.get_engines_supporting_lang()
            cls.initialized = True

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
    def get_engines_supporting_lang(cls,
                                    current_engine_key: ServiceID) -> (
            Tuple[List[Choice], int] | None):
        """
        Gets a list of available engine Choices that support the current kodi language
        Any unavailable engines (broken, uninstalled, etc.) are ommitted.

        :param current_engine_key: id of the currently running engine
        :return:

            TODO: Rework all of the language related methods. There is a ton of
            redundancy in these methods. This is due to the conception of how
            the menus would work. Originally the idea is that you would first
            choose your language from the universe of languages and then drill
            down to the engine that supported your language and finly pick the
            language variant and voice.   Well, it don't work that way...

            Instead, you always choose your Kodi language and territory, etc.
            first. So for TTS, you are presented with the variations of your
            major language ('en') supported by the current engine. The model is
            that you can choose language variant (territory) and voice. You can
            also filter on gender. Of course engines vary widely on how the variants
            and voices are represented and organized. It is a work in progress.

            Anyway, The code here can probably be reduced to two methods:
            1) Discover the language capabilities of each engine, building a
            master table
            2) A method for getting the language info for a specific engine and
            language, based on what was discovered in 1).

            This won't be trivial, but it shouldn't be that big of a job either.
            It will make the code much better.
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'current_engine_key: {current_engine_key}')
        final_choices: List[Choice] = []
        idx: int = 0
        current_choice_index: int = -1

        # Get all language entries (engine=None does that)
        """
            Returns a Dict indexed by setting_id. The values are
            Dict's indexed by language (en, fr, but not en-us).
            Values of this language dict are lists that contain
            all supported variations of a single language (en-us, en-gb...).
            entries_by_engine: key: engine_key
                        value: Dict[lang_family, List[languageInfo]]
                        lang_family (iso-639-1 or -2 code)
                        List[languageInfo} list of all languages supported by 
                        that engine and language ('en' or 'en-us' and other variants).
                        The langInfo includes details about the language, the 
                        voice Id used by the engine, etc.
        """
        try:
            entries = LanguageInfo.get_entries(translate=True,
                                               ordered=True,
                                               engine_key=None)
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'entries: {entries.keys()}')
        except Exception as e:
            MY_LOGGER.exception('')
            entries = {}

        try:
            """
                We display two views. In both cases they are arranged in 
                the display order of the language family, then language, then
                engine display order. So, if we display only language entries
                in the 'en' language family for every engine we have something like:

                    en English, United States eSpeak
                    en English, United States GoogleTTS 

            """
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_language: langcodes.Language
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'kodi_lang: {kodi_lang} kodi_locale: {kodi_locale} '
                                f'kodi_language: {kodi_language}')

            #  Dict[str, Dict[str, List[LanguageInfo]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # and the List of LangInfos

            # First, create sorted list of engines by sorting on their label
            engine_choices: List[Choice] = []
            for engine_key in entries.keys():
                engine_key: ServiceID
                choice: Choice
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine_key: {engine_key} type: {type(engine_key)}')
                engine_label: str = LanguageInfo.get_translated_engine_name(engine_key)
                choice = Choice(label=engine_label, value=engine_key.service_id,
                                choice_index=0, engine_key=engine_key,
                                lang_info=None)
                engine_choices.append(choice)
            engine_choices = sorted(engine_choices, key=lambda entry: entry.label)

            # Now find the closet match of the languages for each engine

            idx: int = 0
            for choice in engine_choices:
                choice: Choice
                engines_langs: List[Choice] = []
                engine_key: ServiceID = choice.engine_key
                current_matching_choice: Choice | None = None
                current_engine_voice_id: str = Settings.get_voice(engine_key)
                current_engine_lang_id: str = Settings.get_language(engine_key)
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine_key: {engine_key} '
                                    f'current_voice: {current_engine_voice_id} '
                                    f'current_lang_id: {current_engine_lang_id}')
                language_entry:  Dict[str, List[LanguageInfo]]
                language_entry = entries[engine_key]

                # We only care about Kodi's language
                languages: List[LanguageInfo] = language_entry.get(kodi_lang)
                if languages is None or len(languages) == 0:
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'Language {kodi_lang} not supported for'
                                        f' this engine: {engine_key}')
                    continue

                # Now find nearest match to current locale kodi_locale

                engine_supported_voices: int = 0
                engine_label: str = ''
                for lang_info in languages:
                    lang_info: LanguageInfo
                    engine_label = lang_info.translated_engine_name
                    engine_supported_voices += 1
                    # Get (text) language differences between the current locale
                    # and the proposed language
                    match_distance: int
                    match_distance = langcodes.tag_distance(desired=kodi_language,
                                                            supported=lang_info.ietf)
                    label = lang_info.label
                    key: str = f'{match_distance:3d}{label} engine: {engine_key}'
                    # Must fix the choice_index later
                    if (MY_LOGGER.isEnabledFor(DEBUG) and
                            engine_key != lang_info.engine_key):
                        MY_LOGGER.debug(f'ERROR: lang_info.service_key: '
                                        f'{lang_info.engine_key} != '
                                        f'current service_key: {engine_key}')
                    choice: Choice
                    choice = Choice(label=label, value=engine_key.service_id,
                                    choice_index=-1,
                                    sort_key=key,
                                    lang_info=lang_info,
                                    engine_key=lang_info.engine_key,
                                    match_distance=match_distance)
                    engines_langs.append(choice)
                    if (current_engine_voice_id == lang_info.engine_voice_id and
                            current_engine_lang_id == lang_info.engine_lang_id):
                        current_matching_choice = choice
                        if MY_LOGGER.isEnabledFor(DEBUG):
                            MY_LOGGER.debug(f'current_engine_lang_id: '
                                            f'{current_engine_lang_id}')

                # Done with creating a list of language variants for an engine
                # which to sort and further manipulate

                # Sort the choices by language match
                if MY_LOGGER.isEnabledFor(DEBUG):
                    MY_LOGGER.debug(f'engine: {engine_key} # lang choices: '
                                    f'{len(engines_langs)}')

                engines_langs = sorted(engines_langs, key=lambda chc: chc.sort_key)
                # Finished processing all langs for an engine
                # Now, simply pick the best match. Since each engine is being
                # processed in sorted order, these entries will be sorted correctly.

                # If we have a saved setting for this engine, then try to use the
                # previous voice_id and lang_id
                matching_choice: Choice | None = None
                if current_matching_choice is not None:
                    for choice_to_check in engines_langs:
                        choice_to_check: Choice
                        if MY_LOGGER.isEnabledFor(DEBUG_V):
                            MY_LOGGER.debug_v(f'current voice: {current_engine_voice_id} '
                                              f'lang_id: {current_engine_lang_id} '
                                              f'distance: {choice.match_distance} '
                                              f'matching_sort_key: '
                                              f'{current_matching_choice.sort_key}')
                            MY_LOGGER.debug_v(f'choice_to_check: {choice_to_check}')
                        if current_matching_choice.sort_key == choice_to_check.sort_key:
                            matching_choice = choice_to_check
                            break

                if matching_choice is None:
                    choice_to_add: Choice = engines_langs[0]
                else:
                    choice_to_add = matching_choice
                choice_to_add.choice_index = idx
                if current_engine_key is not None:
                    if current_engine_key == choice_to_add.engine_key:
                        current_choice_index = idx
                    if MY_LOGGER.isEnabledFor(DEBUG_V):
                        MY_LOGGER.debug_v(f'current_engine_key: {current_engine_key} '
                                          f'idx: {current_choice_index} '
                                          f'choice_key: {choice_to_add.engine_key} '
                                          f'voice: {choice.lang_info.engine_voice_id} '
                                          f'distance: {choice.match_distance}')
                final_choices.append(choice_to_add)
                idx += 1
            # Finished processing all engines

            if MY_LOGGER.isEnabledFor(DEBUG_V):
                for choice in final_choices:
                    MY_LOGGER.debug_v(f'final_choices: {choice}')
            return final_choices, current_choice_index
        except Exception as e:
            MY_LOGGER.exception('')
        return None

    @classmethod
    def get_languages_supporting_engine(cls, engine_key: ServiceID,
                                        best_match_only: bool = False
                                        ) -> Tuple[List[Choice] | None, int | None]:
        """
        Gets a list of language Choices that support the current kodi language

        :param engine_key:  The engine to get language information for
        :param best_match_only: If True then only return the languge information
            for the language that best matches the current Kodi locale for this engine
        :return: A Tuple of a list of language choices and a index for the best
            language choicematch for this engine and locale
        """
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            # Get language entries for just this engine
            """
               Returns a  Dict indexed by setting_id. The values are
               Dict's indexed by language. Values are lists
                 of languages supported by that engine. The list will contain
                 all supported variations of a single language.
                 entries_by_engine: key: setting_id
                            value: Dict[lang_family, List[languageInfo]]
                            lang_family (iso-639-1 or -2 code)
                            List[languageInfo} list of all languages supported by 
                            that engine and language ('en' or 'en-us' and other variants).
                            The langInfo includes details about the language, the 
                            voice Id used by the engine, etc.
            """
            entries = LanguageInfo.get_entries(translate=True,
                                               ordered=True,
                                               lang_family=None,
                                               engine_key=engine_key)
            count: int = 0
            for key, value in entries.items():
                for lang, lang_values in value.items():
                    count += len(lang_values)
        except Exception as e:
            MY_LOGGER.exception('')
            entries = {}
        try:
            """
                We display two views. In both cases they are arranged in 
                the display order of the language family, then language, then
                engine display order. So, if we display only language entries
                in the 'en' language family for every engine we have something like:

                    en English, United States eSpeak
                    en English, United States GoogleTTS 
            """
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_language: langcodes.Language
            #  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # and the List of LangInfos

            idx: int = 0
            sort_choices: List[Choice] = []
            for engine_key, langs_for_an_engine in entries.items():
                engine_key: ServiceID
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    if lang_family_id != kodi_lang:
                        continue

                    engine_supported_voices: int = 0
                    engine_label: str = ''
                    choices: List[Choice] = []
                    for lang_info in engine_langs_in_family:
                        lang_info: LanguageInfo
                        engine_label = lang_info.translated_engine_name
                        engine_supported_voices += 1
                    choice: Choice
                    choice = Choice(label=engine_label, value=engine_key.service_id,
                                    engine_key=engine_key, choice_index=0)
                    if MY_LOGGER.isEnabledFor(DEBUG):
                        MY_LOGGER.debug(f'choice: {choice}')
                    more_choices: List[Choice]
                    more_choices = cls.sort_engine_langs(engine_langs_in_family,
                                                         kodi_language,
                                                         choices)
                    sort_choices.extend(more_choices)
            choices: List[Choice]
            best_idx: int
            choices, best_idx = cls.identify_closet_match(sort_choices, kodi_locale)
            if MY_LOGGER.isEnabledFor(DEBUG):
                for choice in choices:
                    MY_LOGGER.debug(f'choices: {choice.label} {choice.value}')
            return choices, best_idx
        except Exception as e:
            MY_LOGGER.exception('')
        return None, None

    @classmethod
    def get_formatted_label(cls, lang_info: LanguageInfo,
                            kodi_language: langcodes,
                            format_type: FormatType) -> str:
        label: str = ''
        antonym: str = lang_info.autonym
        engine_name: str = lang_info.translated_engine_name
        country_name: str = lang_info.translated_country_name
        if format_type == FormatType.LONG:
            voice_name: str = lang_info.translated_voice
            voice_label: str = MessageId.VOICE.get_msg()
            if antonym != country_name:
                if voice_name in (country_name, antonym):
                    label = (f'{engine_name:10} '
                             f'{country_name:20} '
                             f'{antonym:10}')
                else:
                    label = (f'{engine_name:10} '
                             f'{country_name:20} '
                             f'{antonym:10} '
                             f'{voice_label}  {voice_name:20}')
            else:
                if voice_name in (country_name, antonym):
                    label = (f' {engine_name:10} '
                             f'{country_name:32}')
                else:
                    label = (f' {engine_name:10} '
                             f'{country_name:32}  '
                             f'{voice_label}  {voice_name:20}')
        elif format_type == FormatType.SHORT:
            label = f'{engine_name:10}  {country_name:32}'
        elif format_type == FormatType.DISPLAY:
            label = f'{engine_name:10} {lang_info.get_display_name(kodi_language):32}'
        else:
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'ERROR invalid format_type: {format_type}')
        return label

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        return LanguageInfo.get_formatted_lang(lang)

    @classmethod
    def sort_engine_langs(cls,
                          engine_langs_in_family: List[ForwardRef('LanguageInfo')],
                          kodi_language: langcodes.Language,
                          sort_choices: List[Choice]) -> List[Choice]:
        """
        Sorts language entries for a single engine, returning a list of
        Choices.
        Sorts by match_distance then label.
        Also adds the match distance between Kodi's current language and the
        languages being sorted.

        :param engine_langs_in_family:
        :param kodi_language:
        :param sort_choices:
        :return:
        """
        idx: int = 0
        for lang_info in engine_langs_in_family:
            lang_info: LanguageInfo
            # Get the name of the language in the current language
            # display_current_lang: str = lang_info.ietf.display_name(
            #         language=kodi_language)
            #  display_current_territory: str = lang_info.ietf.territory_name()
            # Get name of the language in its native language
            # display_lang_choice: str = lang_info.ietf.autonym()
            # get how close of a match this language is to
            # Kodi's setting

            match_distance: int
            match_distance = langcodes.tag_distance(desired=kodi_language,
                                                    supported=lang_info.ietf)
            # display_engine_name: str = lang_info.translated_engine_name
            # voice_name: str = lang_info.translated_voice
            label = lang_info.label
            key: str = f'{match_distance:3d}{label}'
            # Must fix the choice_index later
            choice: Choice
            choice = Choice(label=label, value='', choice_index=-1,
                            sort_key=key, lang_info=lang_info,
                            engine_key=lang_info.engine_key,
                            match_distance=match_distance)
            sort_choices.append(choice)

        # Sort the choices by language match
        sorted_choices: List[Choice]
        sorted_choices = sorted(sort_choices, key=lambda chc: chc.sort_key)
        return sorted_choices

    @classmethod
    def pick_closet_match(cls, choices: List[Choice],
                          kodi_locale: str) -> List[Choice]:
        """
        Returns a list of the best language matches from each of the engines
        represented in the choices presented here. Assumes that match information
        is already present. sort_engine_langs can add this information prior to
        call.

        :param choices:
        :param kodi_locale:
        :return:
        """
        best_choice_for_engine: Dict[ServiceID, Choice] = {}
        choice: Choice
        result_choices: List[Choice] = []
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'choices: {choices}')
        for choice in choices:
            lang_info: LanguageInfo = choice.lang_info
            choice.engine_key = lang_info.engine_key
            best_choice: Choice | None = best_choice_for_engine.get(choice.engine_key)
            if best_choice is None:
                best_choice_for_engine[choice.engine_key] = choice
            else:
                if choice.match_distance < best_choice.match_distance:
                    best_choice_for_engine[choice.engine_key] = choice

        result_choices.extend(best_choice_for_engine.values())
        return result_choices

    @classmethod
    def identify_closet_match(cls, sorted_choices: List[Choice],
                              kodi_locale: str) -> Tuple[List[Choice], int]:
        """
        Given a sorted list of languages and variants for a single engine,
        identify the closet language and varient (voice) match and returns
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
        current_engine_voice_id: str = Settings.get_voice(engine_key)
        current_engine_lang_id: str = Settings.get_language(engine_key)
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'engine_key: {engine_key} '
                            f'current_voice: {current_engine_voice_id} '
                            f'current_lang_id: {current_engine_lang_id}')

        current_choice_index: int = -1
        closest_match_index: int = -1
        closest_match: int = 10000
        choice: Choice
        choices: List[Choice] = []
        for choice in sorted_choices:
            lang_info: LanguageInfo = choice.lang_info
            locale: str = lang_info.ietf.to_tag()
            lang_id: str = lang_info.language_id
            choice.engine_key = lang_info.engine_key
            choice.choice_index = idx
            if choice.match_distance < closest_match:
                closest_match = choice.match_distance
                closest_match_index = idx
            if current_choice_index == -1 and locale == kodi_locale:
                current_choice_index = idx
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'engine_key: {engine_key} '
                                f'engine_voice_id: {lang_info.engine_voice_id} '
                                f'lang_id: {lang_info.engine_lang_id}')
            if (current_engine_voice_id == lang_info.engine_voice_id and
                    current_engine_lang_id == lang_info.engine_lang_id):
                current_choice_index = idx

            choices.append(choice)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'{choice}')
            idx += 1

        if current_choice_index == -1:
            current_choice_index = closest_match_index
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'choice_idx: {current_choice_index} choice: '
                            f'{choices[current_choice_index].lang_info.engine_lang_id} '
                            f'{choices[current_choice_index].lang_info.engine_voice_id}')
        return choices, current_choice_index

    @classmethod
    def get_language_choices(cls,
                             engine_key: ServiceID | None = None,
                             get_best_match: bool = False,
                             format_type: FormatType = FormatType.DISPLAY) -> (
            Tuple)[List[Choice] | None, int | None]:

        """
        Gets language capabilities of all or a single TTS engine. The
        returned languages/voices will belong to the same family (English,
        Spanish, etc.) as Kodi is configured. Further, the entries will be
        sorted by how well they match Kodi's locale (language and territory).

        Note that the sort is based upon the written language and does
        not take into account the quality of the voicing made by the entine.

        :param format_type:
        :param engine_key: If None, then return information for all engines
                         If not None, then return information for the engine
                         identified by 'engine'
        :param get_best_match; If True, then return index to best match,
                                 If False, return index to current match,
                                 if available, otherwise, best match.
        :return: List of supported voicings by the engine(s) supporting
            the current language and territory, sorted by how good of a match
            it is to Kodi's current settings. Also, an index to the current
            or best matching entry (see get_best_match).
        """
        if MY_LOGGER.isEnabledFor(DEBUG):
            MY_LOGGER.debug(f'In get_language_choices service_key: {engine_key}')
        choices: List[Choice] = []
        current_choice_index: int = -1
        entries: Dict[ServiceID, Dict[str, List[ForwardRef('LanguageInfo')]]] | None
        entries = None
        try:
            # Get all language entries (engine=None does that)
            entries = LanguageInfo.get_entries(translate=True,
                                               ordered=True,
                                               engine_key=engine_key)
            count: int = 0
            for service_key, value in entries.items():
                service_key: ServiceID  # Identifies the engine which the value belongs
                for lang, lang_values in value.items():
                    lang: str  # Engine can support Multiple langs
                    lang_values: List[LanguageInfo]  # langs can have multiple variants
                    count += len(lang_values)
        except Exception as e:
            MY_LOGGER.exception('')
            entries = {}
        try:
            """
                We display two views. In both cases they are arranged in 
                the display order of the language family, then language, then
                engine display order. So, if we display only language entries
                in the 'en' language family for every engine we have something like:

                    en English, United States eSpeak
                    en English, United States GoogleTTS 
            """
            kodi_lang, kodi_locale, kodi_friendly_locale, kodi_language = \
                LanguageInfo.get_kodi_locale_info()
            kodi_language: langcodes.Language
            #  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo that is within the
            # same language family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # and the List of LangInfo
            for engine_key, langs_for_an_engine in entries.items():
                engine_key: ServiceID
                sort_choices: List[Choice] = []
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    langs_in_family: List[ForwardRef('LanguageInfo')]
                    if lang_family_id != kodi_lang:
                        continue
                    more_chc: List[Choice]
                    cur_idx: int
                    more_chc = cls.sort_engine_langs(langs_in_family,
                                                     kodi_language,
                                                     sort_choices=sort_choices)
                    choices.extend(more_chc)
            match_locale: str = kodi_locale
            current_locale: str = ''
            if not get_best_match:
                current_locale: str = Settings.get_language(engine_key)
                # Convert to ietf format (from en-au to en-AU)
                match_locale = langcodes.Language.get(current_locale).to_tag()
            if MY_LOGGER.isEnabledFor(DEBUG):
                MY_LOGGER.debug(f'get_best_match: {get_best_match} '
                                f'kodi_locale: {kodi_locale} '
                                f'current_locale: {current_locale} '
                                f'match_locale: {match_locale}')
            current_index: int
            sort_choices, current_index = cls.identify_closet_match(choices,
                                                                    match_locale)
            if current_index < 0:
                sort_choices, current_index = cls.identify_closet_match(choices,
                                                                        kodi_locale)
            for choice in sort_choices:
                choice: Choice
                choice.label = cls.get_formatted_label(choice.lang_info,
                                                       format_type=format_type,
                                                       kodi_language=kodi_language)
            return sort_choices, current_index
        except Exception as e:
            MY_LOGGER.exception('')
        return None, None


SettingsHelper.init_class()
