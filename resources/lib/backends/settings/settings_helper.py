# coding=utf-8
from __future__ import annotations

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
from backends.settings.setting_properties import SettingsProperties
from backends.settings.settings_map import SettingsMap
from backends.settings.validators import StringValidator
from common.base_services import BaseServices
from common.debug import Debug
from common.exceptions import LogicError
from common.logger import BasicLogger, DEBUG_XV
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
           Creates a Dictionary of the allowed PlayerMode for a given service.

           The created structure is allowed_player_modes

           The engine and player must both support the same PlayerMode. The UI
           needs to reflect what the current choices are. Side-effects that
           lead to incorrect configurations must be prevented.

           The structure is simple. It is indexed by service_id (engine or
           player). Each value is a list of AllowedValues for PlayerMode for
           that service. The structure is used to see if a combination of
           engine, player and mode are valid. AllowedValue has an enabled
           flag that is False when that PlayerMode can not be used due to
           that other service (engine or player) involved.

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

        if len(cls.allowed_player_modes.keys()) > 0:
            return

        services: List[Tuple[str, str]]
        services = SettingsMap.get_services_for_service_type(ServiceType.ENGINE)
        services.extend(SettingsMap.get_services_for_service_type(ServiceType.PLAYER))
        for service_id, label in services:
            service_id: str
            label: str
            MY_LOGGER.debug(f'service: {service_id} {label}')
            player_mode_val: StringValidator | IStringValidator
            player_mode_val = SettingsMap.get_validator(service_id,
                                                        SettingsProperties.PLAYER_MODE)
            if player_mode_val is None:
                MY_LOGGER.info(f'No PLAYER_MODE validator for: {label}')
                continue
            allowed_player_modes: List[AllowedValue]
            allowed_player_modes = player_mode_val.get_allowed_values()
            cls.allowed_player_modes[service_id] = allowed_player_modes

    @classmethod
    def update_player_mode(cls, engine_id: str, player_id: str,
                           player_mode: PlayerMode
                           ) -> Tuple[PlayerMode | None, List[PlayerMode]]:
        """
        Consults with and updates allowed_player_modes to determine what if any
        changes need to be made to have a valid configuration.

        :param engine_id:  The engine to be used
        :param player_id:  The player to be used
        :param player_mode: The proposed player mode
        :return: Tuple[player_mode, List[AllowedValue]
                 player_mode is the mode to use and the AllowedValues are to
                 be used for UI. List is based upon the engine's modes, but
                 with any unsupported values from the player marked disabled.
        """
        # AllowedValue is complicating things, and probably not useful

        engine_allowed_values: List[AllowedValue] = cls.allowed_player_modes[engine_id]
        player_allowed_values: List[AllowedValue] = cls.allowed_player_modes[player_id]
        engine_player_modes: List[PlayerMode] = []
        player_player_modes: List[PlayerMode] = []
        for allowed_value in engine_allowed_values:
            allowed_value: AllowedValue
            MY_LOGGER.debug(f'playerMode: {allowed_value}')
            if allowed_value.enabled:
                value: PlayerMode = PlayerMode(allowed_value.value)
                MY_LOGGER.debug(f'value: {value} type: {type(value)}')
                engine_player_modes.append(value)
        for allowed_value in player_allowed_values:
            allowed_value: AllowedValue
            MY_LOGGER.debug(f'playerMode2: {allowed_value}')
            if allowed_value.enabled:
                value: PlayerMode = PlayerMode(allowed_value.value)
                MY_LOGGER.debug(f'value2: {value} type: {type(value)}')
                player_player_modes.append(value)

        intersection: List[PlayerMode] = PlayerMode.intersection(engine_player_modes,
                                                                 player_player_modes)
        MY_LOGGER.debug(f'intersection: {intersection}')
        new_player_mode = None
        if len(intersection) != 0 and player_mode not in intersection:
            new_player_mode = intersection[0]
        return new_player_mode, intersection

    '''
    @classmethod
    def get_engine_id(cls):
        """
        Gets the
        :return:
        """
        if cls.service_id is None:
            cls.service_id = Settings.getSetting(SettingsProperties.ENGINE, None,
                                                SettingsProperties.ENGINE_DEFAULT)
        MY_LOGGER.debug(f'service_id: {cls.service_id}')
        valid_engine: bool = False

        if cls.service_id != SettingsProperties.ENGINE_DEFAULT:
            valid_engine = SettingsMap.is_available(cls.service_id)
        # if not valid_engine:
        #     cls.service_id = BackendInfo.getAvailableBackends()[0].service_id
        MY_LOGGER.debug(f'final service_id: {cls.service_id}')
        return cls.service_id
    '''

    @classmethod
    def update_enabled_state(cls, engine_id: str, player_id: str) -> None:
        engine_allowed_values: List[AllowedValue] = cls.allowed_player_modes[engine_id]
        player_allowed_values: List[AllowedValue] = cls.allowed_player_modes[player_id]
        AllowedValue.update_enabled_state(engine_values=engine_allowed_values,
                                          player_values=player_allowed_values)
    @classmethod
    def get_engines_supporting_lang(cls,
                                    current_engine_id: str) -> (
            Tuple[List[Choice], int] | None):
        """
        Gets a list of engine Choices that support the current kodi language

        :param current_engine_id: id of the currently running engine
        :return:
        """
        MY_LOGGER.debug(f'In get_engines_supporting_lang')
        final_choices: List[Choice] = []
        idx: int = 0
        current_choice_index: int = -1

        # Get all language entries (engine=None does that)
        """
            Returns a Dict indexed by service_id. The values are
            Dict's indexed by language (en, fr, but not en-us).
            Values of this language dict are lists that contain
            all supported variations of a single language (en-us, en-gb...).
            entries_by_engine: key: service_id
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
                                               engine_id=None)
        except Exception as e:
            MY_LOGGER.exception('')
            entries = {}

        # MY_LOGGER.debug(f'entries:{entries}')
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

            #  Dict[str, Dict[str, List[LanguageInfo]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # and the List of LangInfos

            '''
            current_value: str = cls.getSetting(SettingsProperties.LANGUAGE,
                                                kodi_locale)
            if current_value == 'unknown':
                current_value = kodi_locale
            current_language: langcodes.Language.get(current_value)
            
            default_setting_index: int = -1
            # MY_LOGGER.debug(f'FLOYD About to sort choices')
            # entries: Dict[str, Dict[str, List[LanguageInfo]]] = None
            '''
            # First, create sorted list of engine keys by sorting on their label
            engine_choices: List[Choice] = []
            for engine_id in entries.keys():
                choice: Choice
                engine_label: str = LanguageInfo.get_translated_engine_name(engine_id)
                choice = Choice(label=engine_label, value=engine_id,
                                choice_index=0, engine_id=engine_id,
                                lang_info=None)
                engine_choices.append(choice)
            engine_choices = sorted(engine_choices, key=lambda entry: entry.label)

            # Now find the closet match of the languages for each engine

            idx: int = 0
            for choice in engine_choices:
                choice: Choice
                engines_langs: List[Choice] = []
                engine_id: str = choice.engine_id
                language_entry:  Dict[str, List[LanguageInfo]]
                language_entry = entries[engine_id]
                # We only care about the current language
                languages: List[LanguageInfo] = language_entry.get(kodi_lang)
                if languages is None:
                    MY_LOGGER.debug(f'Language {kodi_lang} not supported for'
                                      f' this engine: {engine_id}')
                    continue

                # Now find nearest match to current locale kodi_locale

                engine_supported_voices: int = 0
                engine_label: str = ''
                lang_info = None
                for lang_info in languages:
                    lang_info: LanguageInfo
                    engine_label = lang_info.translated_engine_name
                    engine_supported_voices += 1
                    choice: Choice
                    choice = Choice(label=engine_label, value=engine_id,
                                    choice_index=0, engine_id=engine_id,
                                    lang_info=lang_info)
                    engines_langs.append(choice)

                    # Get (text) language differences between the current locale
                    # and the proposed language

                    match_distance: int
                    match_distance = langcodes.tag_distance(desired=kodi_language,
                                                            supported=lang_info.ietf)
                    label = lang_info.label
                    key: str = f'{match_distance:3d}{label}'
                    # Must fix the choice_index later
                    choice: Choice
                    choice = Choice(label=label, value='', choice_index=-1,
                                    sort_key=key, lang_info=lang_info,
                                    engine_id=lang_info.engine_id,
                                    match_distance=match_distance)
                    engines_langs.append(choice)
                # Done with creating a list of language variants for an engine
                # which to sort and further manipulate

                # Sort the choices by language match

                engines_langs = sorted(engines_langs, key=lambda chc: chc.sort_key)
                # Finished processing all langs for an engine
                # Now, simply pick the best match. Since each engine is being
                # processed in sorted order, these entries will be sorted correctly.

                choice_to_add: Choice = engines_langs[0]
                choice_to_add.choice_index = idx
                if current_engine_id == choice_to_add.engine_id:
                    current_choice_index = idx
                MY_LOGGER.debug(f'current_engine_id: {current_engine_id}'
                                f'idx: {current_choice_index}'
                                f'choice_id: {choice_to_add.engine_id}')
                final_choices.append(engines_langs[0])
                idx += 1
            # Finished processing all engines

            for choice in final_choices:
                MY_LOGGER.debug(f'final_choices: {choice}')
            return final_choices, current_choice_index
        except Exception as e:
            MY_LOGGER.exception('')
        return None

    @classmethod
    def get_languages_supporting_engine(cls, engine_id: str,
                                        best_match_only: bool = False
                                        ) -> Tuple[List[Choice] | None, int | None]:
        """
        Gets a list of language Choices that support the current kodi language

        :param engine_id:  The engine to get language information for
        :param best_match_only: If True then only return the languge information
            for the language that best matches the current Kodi locale for this engine
        :return: A Tuple of a list of language choices and a index for the best
            language choicematch for this engine and locale
        """
        MY_LOGGER.debug(f'In get_languages_supporting_engine')
        choices: List[Choice] = []
        current_choice_index: int = -1
        try:
            # Get language entries for just this engine
            """
               Returns a  Dict indexed by service_id. The values are
               Dict's indexed by language. Values are lists
                 of languages supported by that engine. The list will contain
                 all supported variations of a single language.
                 entries_by_engine: key: service_id
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
                                               engine_id=engine_id)
            count: int = 0
            for key, value in entries.items():
                for lang, lang_values in value.items():
                    count += len(lang_values)

            # MY_LOGGER.debug(f'FLOYD # items: {count}')

        except Exception as e:
            MY_LOGGER.exception('')
            entries = {}

        # MY_LOGGER.debug(f'entries:{entries}')
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
            # MY_LOGGER.debug(f'FLOYD kodi_language: {kodi_language} '
            #                   f'Kodi lang: {kodi_lang} '
            #                   f'kodi_locale: {kodi_locale}')

            #  Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]]
            # sorted_keys: List[Tuple[str, str]] = []
            #
            # Top level dict is indexed by engine-id
            # The value is a Dict, indexed by language_id ('en') with value
            # being a List of every LanguageInfo who's language is within the
            # same family as it's key.
            # So to sort, we need to sort both the second level dict's keys
            # and the List of LangInfos

            '''
            current_value: str = cls.getSetting(SettingsProperties.LANGUAGE,
                                                kodi_locale)
            if current_value == 'unknown':
                current_value = kodi_locale
            current_language: langcodes.Language.get(current_value)
            '''
            default_setting_index: int = -1
            # MY_LOGGER.debug(f'FLOYD About to sort choices')
            # entries: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] = None

            idx: int = 0
            sort_choices: List[Choice] = []
            for engine_id, langs_for_an_engine in entries.items():
                engine_id: str
                # MY_LOGGER.debug(f'FLOYD service_id: {service_id}')
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    # MY_LOGGER.debug(f'FLOYD lang_family_id: {lang_family_id}')
                    if lang_family_id != kodi_lang:
                        continue

                    engine_supported_voices: int = 0
                    engine_label: str = ''
                    choices: List[Choice] = []
                    for lang_info in engine_langs_in_family:
                        lang_info: LanguageInfo
                        # def tag_distance(desired: Union[str, Language],
                        #    supported: Union[str, Language]) -> int:
                        #  closest_supported_match(desired_language,
                        #     supported_languages)
                        #  closest_match(desired_language, supported_language)
                        # MY_LOGGER.debug(f'FLOYD lang_info {lang_info.ietf.language}'
                        #                   f' {lang_info.ietf.territory}')
                        engine_label = lang_info.translated_engine_name

                        engine_supported_voices += 1
                    choice: Choice
                    choice = Choice(label=engine_label, value=engine_id,
                                    engine_id=engine_id, choice_index=0)
                    MY_LOGGER.debug(f'choice: {choice}')
                    #  sort_choices.append(choice)

                    more_choices: List[Choice]
                    more_choices = cls.sort_engine_langs(engine_langs_in_family,
                                                         kodi_language,
                                                         choices)
                    sort_choices.extend(more_choices)
            # Sort the choices and fix indices

            choices: List[Choice]
            best_idx: int
            choices, best_idx = cls.identify_closet_match(sort_choices, kodi_locale)
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
        antonym: str = lang_info.ietf.autonym()
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
            label = f'{engine_name:10} {lang_info.ietf.display_name(kodi_language):32}'
        else:
            MY_LOGGER.debug(f'ERROR invalid format_type: {format_type}')
        return label

    @classmethod
    def get_formatted_lang(cls, lang: str) -> str:
        return langcodes.Language.get(lang).display_name()

    @classmethod
    def sort_engine_langs(cls,
                          engine_langs_in_family: List[ForwardRef('LanguageInfo')],
                          kodi_language: langcodes.Language,
                          sort_choices: List[Choice]) -> List[Choice]:
        """
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
            display_current_territory: str = lang_info.ietf.territory_name()
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
            # MY_LOGGER.debug(f'FLOYD'
            #                   f' {lang_info.translated_lang_country_name} '
            #                   f'distance: {match_distance}')
            key: str = f'{match_distance:3d}{label}'
            # Must fix the choice_index later
            choice: Choice
            choice = Choice(label=label, value='', choice_index=-1,
                            sort_key=key, lang_info=lang_info,
                            engine_id=lang_info.engine_id,
                            match_distance=match_distance)
            sort_choices.append(choice)

        # Sort the choices by language match

        # MY_LOGGER.debug(f'FLOYD # sort_choices: {len(sort_choices)}')
        sorted_choices: List[Choice]
        sorted_choices = sorted(sort_choices, key=lambda chc: chc.sort_key)
        # MY_LOGGER.debug(f'FLOYD # sort_choices: {len(sort_choices)}')

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
        best_choice_for_engine: Dict[str, Choice] = {}
        choice: Choice
        result_choices: List[Choice] = []
        MY_LOGGER.debug(f'choices: {choices}')
        for choice in choices:
            lang_info: LanguageInfo = choice.lang_info
            choice.engine_id = lang_info.engine_id
            best_choice: Choice | None = best_choice_for_engine.get(choice.engine_id)
            if best_choice is None:
                best_choice_for_engine[choice.engine_id] = choice
            else:
                if choice.match_distance < best_choice.match_distance:
                    best_choice_for_engine[choice.engine_id] = choice

        result_choices.extend(best_choice_for_engine.values())
        return result_choices

    @classmethod
    def identify_closet_match(cls, sorted_choices: List[Choice],
                              kodi_locale: str) -> Tuple[List[Choice], int]:
        """
        Identifies the closet language match in the given choices and returns
        an index to it. Also adds information from lang_info to the Choices.

        Requires that match information already be set prior to call. See
        sort_engine_langs

        :param sorted_choices:
        :param kodi_locale:
        :return:
        """
        idx: int = 0
        current_choice_index: int = -1
        closest_match_index: int = -1
        closest_match: int = 10000
        choice: Choice
        choices: List[Choice] = []
        for choice in sorted_choices:
            lang_info: LanguageInfo = choice.lang_info
            locale: str = lang_info.ietf.to_tag()
            lang_id: str = lang_info.language_id
            choice.engine_id = lang_info.engine_id
            choice.choice_index = idx
            # MY_LOGGER.debug(f'FLOYD lang_id: {lang_id} current_lang: {kodi_lang}')
            if choice.match_distance < closest_match:
                closest_match = choice.match_distance
                closest_match_index = idx
            if current_choice_index == -1 and locale == kodi_locale:
                current_choice_index = idx

            choices.append(choice)
            if MY_LOGGER.isEnabledFor(DEBUG_XV):
                MY_LOGGER.debug_xv(f'{choice}')
            idx += 1

        # MY_LOGGER.debug(f'current_choice_index: {current_choice_index} '
        #                   f'closest_match_idx: {closest_match_index} '
        #                   f'closest_match: {closest_match}')
        if current_choice_index == -1:
            current_choice_index = closest_match_index
        return choices, current_choice_index

    @classmethod
    def get_language_choices(cls,
                             engine_id: str | None = None,
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
        :param engine_id: If None, then return information for all engines
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

        # MY_LOGGER.debug(f'In get_language_choices')
        choices: List[Choice] = []
        current_choice_index: int = -1
        entries: Dict[str, Dict[str, List[ForwardRef('LanguageInfo')]]] | None = None
        try:
            # Get all language entries (engine=None does that)
            entries = LanguageInfo.get_entries(translate=True,
                                               ordered=True,
                                               engine_id=engine_id)
            count: int = 0
            for key, value in entries.items():
                for lang, lang_values in value.items():
                    count += len(lang_values)
                    # MY_LOGGER.debug(f'key: {key} lang:{lang} '
                    #                   f'# values {len(lang_values)}')

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
            # and the List of LangInfos
            for engine_id, langs_for_an_engine in entries.items():
                engine_id: str
                #  MY_LOGGER.debug(f'FLOYD service_id: {service_id}')
                sort_choices: List[Choice] = []
                langs_for_an_engine: Dict[str, List[ForwardRef('LanguageInfo')]]
                for lang_family_id, engine_langs_in_family in langs_for_an_engine.items():
                    lang_family_id: str
                    engine_langs_in_family: List[ForwardRef('LanguageInfo')]
                    # MY_LOGGER.debug(f'FLOYD lang_family_id: {lang_family_id} '
                    #                   f'kodi_lang: {kodi_lang}')
                    if lang_family_id != kodi_lang:
                        continue
                    more_chc: List[Choice]
                    cur_idx: int
                    more_chc = cls.sort_engine_langs(engine_langs_in_family,
                                                     kodi_language,
                                                     sort_choices=sort_choices)
                    choices.extend(more_chc)
            match_locale: str = kodi_locale
            if not get_best_match:
                current_locale: str = Settings.get_language(engine_id)
                # Convert to ietf format (from en-au to en-AU)
                match_locale = langcodes.Language.get(current_locale).to_tag()
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

    '''
    @classmethod
    def getSetting(cls, setting_id, default=None):
        """

        :param setting_id:
        :param default:
        :return:
        """
        engine: ITTSBackendBase = cls.get_engine_class(cls.service_id)
        value = None
        try:
            if default is None:
                default = engine.get_setting_default(setting_id)
            value = engine.getSetting(setting_id, default)
        except AttributeError:
            value = None
        return value

    @classmethod
    def get_engine_class(cls, service_id=None) -> ITTSBackendBase:
        """

        :param service_id:
        :return:
        """
        engine_id: str = None
        if service_id is None:
            service_id = cls.service_id

        if cls.engine_instance is None or cls.engine_instance.engine_id != service_id:
            engine_id: str = None
            if cls.engine_instance is not None:
                engine_id = cls.engine_instance.engine_id
        if service_id is None or engine_id is None:
            Debug.dump_current_thread()
            MY_LOGGER.debug(f'service_id changed to: {service_id} from: {engine_id}')
            cls.engine_instance = BaseServices.getService(service_id)
        return cls.engine_instance
    '''

SettingsHelper.init_class()
